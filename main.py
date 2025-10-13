import argparse
import requests
import json
import base64
from util import extract_public_key, verify_artifact_signature
from merkle_proof import DefaultHasher, verify_consistency, verify_inclusion, compute_leaf_hash

REKOR_URL = "https://rekor.sigstore.dev"


def rekuest(URL, params=None):
    try:
        resp = requests.get(f"{REKOR_URL}{URL}", params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        Exception("Unable to make Rekor API request:", e)


def get_log_entry(log_index, debug=False):
    # verify that log index value is sane
    data = rekuest("/api/v1/log/entries", {"logIndex": log_index})
    return data[list(data.keys())[0]]


def get_verification_proof(log_index, debug=False):
    log_data = get_log_entry(log_index, debug)

    proof = log_data["verification"]["inclusionProof"]
    return proof


def inclusion(log_index, artifact_filepath, debug=False):
    # verify that log index and artifact filepath values are sane
    log_data = get_log_entry(log_index, debug)
    _body = log_data['body']
    body_json = json.loads(base64.b64decode(_body))

    _sig = body_json['spec']['signature']['content']
    signature = base64.b64decode(_sig)

    _cert = body_json['spec']['signature']['publicKey']['content']
    certificate = base64.b64decode(_cert)

    public_key = extract_public_key(certificate)

    try:
        verify_artifact_signature(signature, public_key, artifact_filepath)
    except Exception as e:
        print("Artifact signature verification failed:", e)

    proof = get_verification_proof(log_index)

    tree_size = proof['treeSize']
    leaf_hash = compute_leaf_hash(_body)
    root_hash = proof['rootHash']
    hashes = proof['hashes']
    index = proof['logIndex']

    try:
        verify_inclusion(DefaultHasher, index, tree_size,
                         leaf_hash, hashes, root_hash)
    except Exception as e:
        print("Verify Inclusion failed:", e)

    print("Offline verification successful")


def get_latest_checkpoint(debug=False):
    data = rekuest("/api/v1/log")
    return data


def consistency(prev_checkpoint, debug=False):
    # verify that prev checkpoint is not empty
    # get_latest_checkpoint()
    chkpoint = get_latest_checkpoint(debug)
    size1 = prev_checkpoint['treeSize']
    size2 = chkpoint['treeSize']

    root1 = prev_checkpoint['rootHash']
    root2 = chkpoint['rootHash']

    proof = rekuest("/api/v1/log/proof", {
        "lastSize": size2,
        "firstSize": size1,
        "treeID": chkpoint["treeID"]
    })['hashes']

    try:
        verify_consistency(DefaultHasher, size1, size2, proof, root1, root2)
    except Exception as e:
        print("Consistency verification failed:", e)

    print("Consitency verification successful")


def main():
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
