# Python Rekor Monitor Template
Github: [https://github.com/stupendoussuperpowers/scss_hw1.git]()

Lightweight CLI tool for interacting with Rekor Transparency Logs. 

For more information on Rekor and Sigstore, please refer to the following documentation: [Rekor](https://docs.sigstore.dev/logging/overview/), [Sigstore](https://docs.sigstore.dev/)

## Features 

This tool provides the following features for Rekor:

- Verify inclusion proofs for log entries. 
- Verify consistency between checkpoints. 
- Fetch lastest checkpoints. 

## Usage 

`python main.py <options>`

|Option| Description|
-------|-------------|
-d, --debug | Enable debug logs |
-c, --checkpoint | Retrieve latest checkpoint. |
--inclusion <index> | Verify inclusion proof for log entry.|
--artifact <path> | Artifact file path for signature verification. |
--consistency <--tree-id> <--tree-size> <--root-hash>| Verify consistency between checkpoints|

## Building from source

```
git clone https://github.com/stupendoussuperpowers/scss_hw1.git`
cd scss_hw1
pip install -r requirements.txt
```

## Contributing

Please refer to [CONTRIBUTING.md](CONTRIBUTING.md) for a detailed guide on how to contribute to this project. 

If reporting a securty issue, please refer to [SECURTY.md](SECURITY.md). 

