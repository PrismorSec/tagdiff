# TagDiff

TagDiff compares GitHub release notes between two version tags and lets you search through changelogs by keyword.

## What It Does
- Fetches releases from GitHub for a repository
- Compares releases between `old_version` and `new_version`
- Search changelogs by keyword across version ranges
- Returns results as JSON or formatted CLI output
- Caches GitHub API responses locally to avoid repeated fetches
- Uses one shared core function for package, CLI, and Docker

## Project Structure
- `tagdiff/core.py`: shared logic (`get_changelog`, `search_changelogs`)
- `tagdiff/cli.py`: CLI wrapper
- `tagdiff/__init__.py`: package export
- `pyproject.toml`: package + CLI entrypoint config
- `Dockerfile`: Docker image setup

## Install

### From PyPI
```bash
pip install tagdiff
```
https://pypi.org/project/tagdiff/

### From source
```bash
pip install .
```

### Editable (development)
```bash
pip install -e .
```

## Usage

### Diff: Compare releases between two tags

```bash
tagdiff psf/requests v2.31.0 v2.32.0
```

With AI-structured changelog:
```bash
tagdiff psf/requests v2.31.0 v2.32.0 --structured --model gpt-4o
```

Save to file:
```bash
tagdiff psf/requests v2.31.0 v2.32.0 --output result.json
```

### Search: Find keywords across changelogs

Search between two versions:
```bash
tagdiff search psf/requests "bug fix" --from v2.31.0 --to v2.32.3
```

Search from a version onwards:
```bash
tagdiff search psf/requests "deprecat" --from v2.31.0
```

Search up to a version:
```bash
tagdiff search psf/requests "SSL" --to v2.32.3
```

Search all releases:
```bash
tagdiff search psf/requests "security"
```

Output as JSON:
```bash
tagdiff search psf/requests "fix" --from v2.31.0 --to v2.32.3 --json
```

Save search results to file:
```bash
tagdiff search psf/requests "fix" --from v2.31.0 --json --output results.json
```

Case-sensitive search:
```bash
tagdiff search psf/requests "SSL" --case-sensitive
```

### Caching

Add `--cache` to any command to cache GitHub API responses locally in `~/.cache/tagdiff`. This avoids hitting the API repeatedly for the same repo.

```bash
# First run fetches from GitHub and caches
tagdiff search psf/requests "fix" --from v2.31.0 --to v2.32.3 --cache

# Subsequent runs use the cache (instant)
tagdiff search psf/requests "SSL" --from v2.31.0 --to v2.32.3 --cache

# Also works with diff
tagdiff psf/requests v2.31.0 v2.32.0 --cache
```

Set a custom TTL (in seconds, default is 3600 = 1 hour):
```bash
tagdiff search psf/requests "fix" --cache --cache-ttl 86400  # 24 hours
```

Clear the cache:
```bash
# Clear all cached data
tagdiff clear-cache

# Clear cache for a specific repo
tagdiff clear-cache psf/requests
```

Override the cache directory with the `TAGDIFF_CACHE_DIR` environment variable.

### CLI output example

```
  Search: "fix" in psf/requests (v2.31.0 -> v2.32.3)
  Searched 5 releases, found 10 match(es) across 3 release(s)

  v2.32.0  (2024-05-20)  [6 match(es)]
  ──────────────────────────────────────────────────
    - Fixed an issue where setting `verify=False` on the first request from a
    **Bugfixes**
    - Fixed bug in length detection where emoji length was incorrectly
    - Fixed deserialization bug in JSONDecodeError. (#6629)
    - Fixed bug where an extra leading `/` (path separator) could lead
    - Various typo fixes and doc improvements.

  v2.32.1  (2024-05-21)  [1 match(es)]
  ──────────────────────────────────────────────────
    **Bugfixes**

  v2.32.3  (2024-05-29)  [3 match(es)]
  ──────────────────────────────────────────────────
    **Bugfixes**
    - Fixed bug breaking the ability to specify custom SSLContexts in sub-classes of
    - Fixed issue where Requests started failing to run on Python versions compiled

  Total: 10 match(es) in 3 release(s)
```

## Run as module
```bash
python -m tagdiff.cli psf/requests v2.31.0 v2.32.0
python -m tagdiff.cli search psf/requests "fix" --from v2.31.0
```

## Run with Docker
```bash
docker build -t tagdiff-local .
docker run --rm tagdiff-local psf/requests v2.31.0 v2.32.0
docker run --rm tagdiff-local search psf/requests "fix" --from v2.31.0
```

## Use as a library
```python
from tagdiff import get_changelog, search_changelogs, clear_cache

# Diff between versions
result = get_changelog("psf/requests", "v2.31.0", "v2.32.0")

# Search changelogs
result = search_changelogs("psf/requests", "SSL", from_version="v2.31.0", to_version="v2.32.3")

# With caching
result = get_changelog("psf/requests", "v2.31.0", "v2.32.0", cache=True)
result = search_changelogs("psf/requests", "SSL", cache=True, cache_ttl=86400)

# Clear cache
clear_cache()                     # all
clear_cache(repo="psf/requests")  # specific repo
```

## Environment Variables
- `GITHUB_TOKEN` - GitHub API token (recommended, avoids rate limits)
- `TAGDIFF_MODEL` - Default AI model for `--structured` (default: `gpt-4o-mini`)
- `TAGDIFF_CACHE_DIR` - Custom cache directory (default: `~/.cache/tagdiff`)
