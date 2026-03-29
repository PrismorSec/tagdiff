# TagDiff

[![PyPI](https://img.shields.io/pypi/v/tagdiff)](https://pypi.org/project/tagdiff/)
[![Python](https://img.shields.io/pypi/pyversions/tagdiff)](https://pypi.org/project/tagdiff/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

TagDiff compares GitHub release notes between two version tags, lets you search through changelogs by keyword, and can deep-research changes using AI.

## What It Does
- Fetches releases from GitHub for a repository
- Compares releases between `old_version` and `new_version`
- Search changelogs by keyword across version ranges
- Deep-research mode: AI-powered analysis of changelogs + code diffs
- Returns results as JSON or formatted CLI output
- Caches GitHub API responses locally to avoid repeated fetches
- Uses one shared core function for package, CLI, and Docker

## Project Structure
```
tagdiff/
├── config.py       # Environment, constants (cache dir, default model, dotenv)
├── cache.py        # File-based caching (read, write, clear)
├── github.py       # GitHub API (fetch releases, fetch compare diff)
├── releases.py     # Version range filtering
├── llm.py          # LLM calls (structured extraction, streaming analysis)
├── changelog.py    # Diff logic (get_changelog, get_changes_between_versions)
├── search.py       # Keyword search across changelogs
├── analyze.py      # Agentic deep-research pipeline
├── formatter.py    # CLI output formatting
├── cli.py          # CLI entry point (arg parsing + routing)
└── __init__.py     # Public API exports
```

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
tagdiff psf/requests v2.31.0 v2.32.0 --structured --model gpt-5-nano
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

### Analyze: AI-powered deep research

Ask a natural language question about what changed across versions. TagDiff gathers the changelogs (and optionally the actual code diff), then uses an LLM to produce a structured analysis.

Basic analysis:
```bash
tagdiff analyze psf/requests "What SSL and security changes happened?" --from v2.31.0 --to v2.32.3
```

With code diff context (fetches commits + changed files from GitHub compare API):
```bash
tagdiff analyze psf/requests "What breaking changes should I worry about?" --from v2.31.0 --to v2.32.3 --with-diff
```

Use a specific model:
```bash
tagdiff analyze psf/requests "Summarize all deprecations" --from v2.31.0 --to v2.32.3 --model gpt-5-nano
```

Only from-version (analyzes everything after):
```bash
tagdiff analyze psf/requests "What changed in auth?" --from v2.31.0
```

Save analysis to file:
```bash
tagdiff analyze psf/requests "Migration guide from v2.31 to v2.32" --from v2.31.0 --to v2.32.3 --output migration.md
```

Get full result as JSON:
```bash
tagdiff analyze psf/requests "What changed?" --from v2.31.0 --to v2.32.3 --json
```

#### How it works

The analyze command runs a multi-step pipeline:

```
  [1] Fetching releases for psf/requests...
       Found 5 releases: v2.31.0 -> v2.32.3

  [2] Collecting changelogs...
       Collected 5 changelogs (6833 chars)

  [3] Fetching code diff from GitHub...        # only with --with-diff
       139 commits, 78 files changed

  [4] Analyzing with gpt-5-nano...

  **Summary**
  Between v2.31.0 and v2.32.3, the major SSL changes include...

  **Detailed Analysis**
  ...version-by-version breakdown...

  **Key Findings**
  - verify=True now reuses a global SSLContext...
  - Custom SSLContext support was broken and fixed in v2.32.3...

  **Impact Assessment**
  - Users with custom SSLContext subclasses should upgrade to v2.32.3...
```

The LLM response is streamed to the terminal in real-time.

### Caching

Add `--cache` to any command to cache GitHub API responses locally in `~/.cache/tagdiff`. This avoids hitting the API repeatedly for the same repo. Works with `diff`, `search`, and `analyze`.

```bash
# First run fetches from GitHub and caches
tagdiff search psf/requests "fix" --from v2.31.0 --to v2.32.3 --cache

# Subsequent runs use the cache (instant)
tagdiff search psf/requests "SSL" --from v2.31.0 --to v2.32.3 --cache

# Great for analyze — iterate on questions without re-fetching
tagdiff analyze psf/requests "What broke?" --from v2.31.0 --to v2.32.3 --cache
tagdiff analyze psf/requests "What about SSL?" --from v2.31.0 --to v2.32.3 --cache
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

### CLI output example (search)

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
python -m tagdiff.cli analyze psf/requests "What changed?" --from v2.31.0 --to v2.32.3
```

## Run with Docker
```bash
docker build -t tagdiff-local .
docker run --rm tagdiff-local psf/requests v2.31.0 v2.32.0
docker run --rm tagdiff-local search psf/requests "fix" --from v2.31.0
docker run --rm -e OPENAI_API_KEY tagdiff-local analyze psf/requests "What changed?" --from v2.31.0 --to v2.32.3
```

## Use as a library
```python
from tagdiff import get_changelog, search_changelogs, analyze_changelog, clear_cache

# Diff between versions
result = get_changelog("psf/requests", "v2.31.0", "v2.32.0")

# Search changelogs
result = search_changelogs("psf/requests", "SSL", from_version="v2.31.0", to_version="v2.32.3")

# Deep research with AI
result = analyze_changelog("psf/requests", "What SSL changes happened?",
                           from_version="v2.31.0", to_version="v2.32.3",
                           with_diff=True, model="gpt-5-nano")

# With caching
result = get_changelog("psf/requests", "v2.31.0", "v2.32.0", cache=True)
result = search_changelogs("psf/requests", "SSL", cache=True, cache_ttl=86400)
result = analyze_changelog("psf/requests", "What changed?",
                           from_version="v2.31.0", cache=True)

# Clear cache
clear_cache()                     # all
clear_cache(repo="psf/requests")  # specific repo
```

## Environment Variables
- `GITHUB_TOKEN` - GitHub API token (recommended, avoids rate limits)
- `TAGDIFF_MODEL` - Default AI model for `--structured` and `analyze` (default: `gpt-5-nano`)
- `TAGDIFF_CACHE_DIR` - Custom cache directory (default: `~/.cache/tagdiff`)

---

Built by the [Prismor](https://prismor.dev) team.
