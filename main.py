"""
Entrypoint to the rekor CLI util.
"""

import argparse
import json
import base64
import requests
from util import extract_public_key, verify_artifact_signature
from merkle_proof import DefaultHasher, verify_consistency, \
    verify_inclusion, compute_leaf_hash, RootMismatchError

REKOR_URL = "https://rekor.sigstore.dev"


def rekor_request(url, params=None, debug=False):
    """Util function to make requests to rekor."""
    try:
        resp = requests.get(f"{REKOR_URL}{url}", params=params, timeout=10)
        resp.raise_for_status()

        json_resp = resp.json()
        if debug:
            print(f"Response from {url}: {json_resp}")
        return json_resp
    except requests.HTTPError as err:
        print("Rekor returned invalid response:", err)
        return None
    except TimeoutError as err:
        print("Rekor request timed out:", err)
        return None


def get_log_entry(log_index, debug=False):
    """
    Fetch and return the rekor log entry for a given index.

    Input:
        log_index   (int)   -   Log index to lookup.
        debug       (bool)  -   Output debug logs.
    Returns:
        (object)            -   Rekor entry log.
    """
    # verify that log index value is sane
    data = rekor_request("/api/v1/log/entries",
                         {"logIndex": log_index}, debug=debug)
    return data[list(data.keys())[0]]


def get_verification_proof(log_index, debug=False):
    """
    Return the inclusion proof stored for a given log. 

    Input:
        log_index   (int)   -   Log index to lookup.
        debug       (bool)  -   Output debug logs.
    Returns:
        (object)            -   Inclusion proof for the log entry.
    """
    log_data = get_log_entry(log_index, debug)

    proof = log_data["verification"]["inclusionProof"]
    return proof


def inclusion(log_index, artifact_filepath, debug=False):
    """
    Verify the inclusion proof for a given log.

    Input:
        log_index           (int)   -   Log index to verify.
        artifact_filepath   (str)   -   artifact to verify.
        debug               (bool)  -   Output debug logs.
    Returns:
        (bool)                      -   Status of verification.
    """
    # verify that log index and artifact filepath values are sane
    log_data = get_log_entry(log_index, debug)
    log_body = log_data['body']
    log_json = json.loads(base64.b64decode(log_body))

    sig_raw = log_json['spec']['signature']['content']
    signature = base64.b64decode(sig_raw)

    cert_raw = log_body['spec']['signature']['publicKey']['content']
    certificate = base64.b64decode(cert_raw)

    public_key = extract_public_key(certificate)

    if not verify_artifact_signature(signature, public_key, artifact_filepath):
        return False

    proof = get_verification_proof(log_index)
    if not proof:
        return False

    leaf_hash = compute_leaf_hash(log_body)

    try:
        verify_inclusion(
            DefaultHasher,
            proof['logIndex'],
            proof['treeSize'],
            leaf_hash,
            proof['hashes'],
            proof['rootHash']
        )
    except RootMismatchError as e:
        if debug:
            print("Verify Inclusion failed:", e)
        return False

    print("Offline verification successful")
    return True


def get_latest_checkpoint(debug=False):
    """
    Get the latest checkpoint from Rekor's log.

    Returns:
        (object)    -       Body for the latest checkpoint.
    """
    data = rekor_request("/api/v1/log", debug=debug)
    return data


def consistency(prev_checkpoint, debug=False):
    """
    Check if the input checkpoint is consistent with the
    latest checkpoint on Rekor.

    Input:
        prev_checkpoint (object)    -   Checkpoint: {
                                            treeSize,
                                            rootHash,
                                            treeID,
                                        }
    Returns:
        (object)                    -   Body for the latest checkpoint.
    """
    # verify that prev checkpoint is not empty
    # get_latest_checkpoint()
    chkpoint = get_latest_checkpoint(debug)
    size1 = prev_checkpoint['treeSize']
    size2 = chkpoint['treeSize']

    root1 = prev_checkpoint['rootHash']
    root2 = chkpoint['rootHash']

    proof = rekor_request("/api/v1/log/proof", {
        "lastSize": size2,
        "firstSize": size1,
        "treeID": chkpoint["treeID"]
    })['hashes']

    try:
        verify_consistency(DefaultHasher, size1, size2, proof, root1, root2)
    except RootMismatchError as e:
        print("Consistency verification failed:", e)

    print("Consitency verification successful")


def main():
    """CLI parsing"""
    debug = False
    parser = argparse.ArgumentParser(description="Rekor Verifier")
    parser.add_argument('-d', '--debug', help='Debug mode',
                        required=False, action='store_true')  # Default false
    parser.add_argument('-c', '--checkpoint', help='Obtain latest checkpoint\
                        from Rekor Server public instance',
                        required=False, action='store_true')
    parser.add_argument('--inclusion', help='Verify inclusion of an\
                        entry in the Rekor Transparency Log using log index\
                        and artifact filename.\
                        Usage: --inclusion 126574567',
                        required=False, type=int)
    parser.add_argument('--artifact', help='Artifact filepath for verifying\
                        signature',
                        required=False)
    parser.add_argument('--consistency', help='Verify consistency of a given\
                        checkpoint with the latest checkpoint.',
                        action='store_true')
    parser.add_argument('--tree-id', help='Tree ID for consistency proof',
                        required=False)
    parser.add_argument('--tree-size', help='Tree size for consistency proof',
                        required=False, type=int)
    parser.add_argument('--root-hash', help='Root hash for consistency proof',
                        required=False)
    args = parser.parse_args()
    if args.debug:
        debug = True
        print("enabled debug mode")
    if args.checkpoint:
        # get and print latest checkpoint from server
        # if debug is enabled, store it in a file checkpoint.json
        checkpoint = get_latest_checkpoint(debug)
        print(json.dumps(checkpoint, indent=4))
    if args.inclusion:
        inclusion(args.inclusion, args.artifact, debug)
    if args.consistency:
        if not args.tree_id:
            print("please specify tree id for prev checkpoint")
            return
        if not args.tree_size:
            print("please specify tree size for prev checkpoint")
            return
        if not args.root_hash:
            print("please specify root hash for prev checkpoint")
            return

        prev_checkpoint = {}
        prev_checkpoint["treeID"] = args.tree_id
        prev_checkpoint["treeSize"] = args.tree_size
        prev_checkpoint["rootHash"] = args.root_hash

        consistency(prev_checkpoint, debug)


if __name__ == "__main__":
    main()
