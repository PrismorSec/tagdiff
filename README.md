# TagDiff

TagDiff compares GitHub release notes between two version tags.

## What It Does
- Fetches releases from GitHub for a repository
- Compares releases between `old_version` and `new_version`
- Returns a JSON changelog result
- Uses one shared core function for package, CLI, and Docker

## Project Structure
- `tagdiff/core.py`: shared logic (`get_changelog`)
- `tagdiff/cli.py`: CLI wrapper
- `tagdiff/__init__.py`: package export
- `pyproject.toml`: package + CLI entrypoint config
- `Dockerfile`: Docker image setup
- `startup.txt`: quick start commands

## Install
```powershell
python -m pip install .
```

## Run (CLI)
```powershell
tagdiff owner/repo old_version new_version
```

Example:
```powershell
tagdiff psf/requests v2.31.0 v2.32.0
```

## Run (Module)
```powershell
python -m tagdiff.cli psf/requests v2.31.0 v2.32.0
```

## Run (Docker)
```powershell
docker build -t tagdiff-local .
docker run --rm tagdiff-local psf/requests v2.31.0 v2.32.0
```

## Use Core Function Directly
```python
from tagdiff import get_changelog

result = get_changelog("psf/requests", "v2.31.0", "v2.32.0")
print(result)
```
