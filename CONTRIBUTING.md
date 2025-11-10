# Contribution Guide 

We welcome bug fixes, feature requests, documentation improvements and tests. 

## Getting Started 

- Fork this repository. 
- Create a feature branch for each new feature or improvement. 

## Development Setup 

```
python -m venv venv 
source venv/bin/activate 
pip install -r requirements.txt
```

## Before Filing a Pull Request 

1. Make sure that you have filed an issue on the repo which documents at least the following information: 
- Clear title and description 
- Logs for failing cases in case of a bug report. 
- Proposed interface for the new feature. 

2. Make sure your code follows PEP8 style guides. Considering using a linter such as `pylint` or `ruff`. 

3. Make sure your PR includes any required changes to documentation. 

4. Ensure proper test are added and that tests are passing. 

## Filing a security patch 

Please refer to [SECURITY.md](SECURITY.md) for a detailed guide on reporting security vulnerabilities. 
