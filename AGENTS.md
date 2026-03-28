# TagDiff — Agent Deep Research Guide

TagDiff gives you structured access to GitHub release changelogs and code diffs. Use it as your **data extraction layer** — you are the LLM, so skip the `--model` / `--structured` flags entirely and analyze the raw data yourself.

## What TagDiff Does For You

TagDiff fetches, caches, and structures data from GitHub's Releases and Compare APIs. It handles pagination, rate limits, caching, and version range filtering. You get clean JSON back.

**You do NOT need an API key for any of the commands below.** The only optional env var is `GITHUB_TOKEN` for higher GitHub rate limits.

## Core Commands (No LLM Needed)

### 1. Diff: Get Raw Changelogs Between Two Versions

```bash
tagdiff <owner/repo> <old_tag> <new_tag> --cache
```

Returns JSON with all release notes between the two tags. Do NOT use `--structured` (that calls an external LLM — you are the LLM).

**Example:**

```bash
tagdiff langchain-ai/langchain v0.1.0 v0.2.0 --cache
```

**You get back:**

```json
{
  "repo": "langchain-ai/langchain",
  "old_version": "v0.1.0",
  "new_version": "v0.2.0",
  "releases_between": 12,
  "changelogs": [
    {"tag": "v0.1.1", "date": "2024-01-15", "body": "## What's Changed\n- Fixed ..."},
    ...
  ]
}
```

Read this JSON yourself and extract what matters.

### 2. Search: Find Keywords Across Releases

```bash
tagdiff search <owner/repo> "<keyword>" --from <tag> --to <tag> --json --cache
```

Returns matching changelog lines. Use this to narrow down before doing deep analysis.

**Example — find all security-related changes:**

```bash
tagdiff search openai/openai-python "security" --from v1.0.0 --to v1.30.0 --json --cache
```

**You get back:**

```json
{
  "repo": "openai/openai-python",
  "keyword": "security",
  "total_matches": 7,
  "releases_matched": 3,
  "releases_searched": 28,
  "matches": [
    {
      "tag": "v1.12.0",
      "published_at": "2024-03-01T...",
      "matching_lines": ["- Fixed security issue in token handling", "- Security: added input validation"],
      "match_count": 2
    },
    ...
  ]
}
```

**Useful flags:**

- `--case-sensitive` — exact case matching
- `--from` / `--to` — version range (inclusive, both optional)
- `--json` — machine-readable output (always use this)
- `--cache` — avoid re-fetching (always use this)

### 3. Fetch Code Diff (Commits + Changed Files)

There is no standalone "get me just the diff" command, but you can use the Python API directly:

```bash
python3 -c "
from tagdiff.github import fetch_compare
import json
result = fetch_compare('owner/repo', 'v1.0.0', 'v2.0.0')
print(json.dumps(result, indent=2))
"
```

**You get back:**

```json
{
  "total_commits": 142,
  "commits": [
    {"sha": "a1b2c3d", "message": "Fix auth token refresh", "author": "dev1"},
    ...
  ],
  "total_files_changed": 87,
  "files": [
    {"filename": "src/auth.py", "status": "modified", "additions": 42, "deletions": 18},
    {"filename": "src/legacy.py", "status": "deleted", "additions": 0, "deletions": 200},
    ...
  ]
}
```

This is the same data `--with-diff` sends to an external LLM. Instead of paying for that, analyze it yourself.

### 4. Cache Management

```bash
tagdiff clear-cache                    # Clear all cached data
tagdiff clear-cache langchain-ai/langchain  # Clear specific repo
```

Cache lives at `~/.cache/tagdiff/`. Default TTL is 1 hour. Override with `--cache-ttl 86400` (seconds).

---

## Deep Research Playbook

When a user asks you to research what changed in a library, follow this pattern:

### Step 1: Search for relevant changes

```bash
tagdiff search <repo> "<keyword>" --from <tag> --to <tag> --json --cache
```

Scan the `matching_lines` to identify which versions have relevant changes. This is fast and cheap (single GitHub API call if cached).

### Step 2: Get full changelogs for the relevant range

```bash
tagdiff <repo> <start_tag> <end_tag> --cache
```

Read the full JSON output. Parse each changelog entry yourself — you are better at understanding context than `--structured` mode anyway.

### Step 3: Get the code diff if needed

```bash
python3 -c "
from tagdiff.github import fetch_compare
import json
result = fetch_compare('<repo>', '<start_tag>', '<end_tag>')
print(json.dumps(result, indent=2))
"
```

Cross-reference commit messages and changed files against changelog entries to identify what actually changed in code vs. what was documented.

### Step 4: Synthesize your analysis

You now have:

- Matching changelog lines (from search)
- Full release notes (from diff)
- Commit messages + changed file list (from compare)

Combine these to answer the user's question with specific version references, commit hashes, and file paths.

---

## Example: Full Research Flow

User asks: _"What breaking changes happened in FastAPI between 0.100.0 and 0.110.0?"_

```bash
# Step 1: Search for breaking changes
tagdiff search tiangolo/fastapi "breaking" --from 0.100.0 --to 0.110.0 --json --cache

# Step 2: Also search for deprecations (often precede breaking changes)
tagdiff search tiangolo/fastapi "deprecat" --from 0.100.0 --to 0.110.0 --json --cache

# Step 3: Get full changelogs
tagdiff tiangolo/fastapi 0.100.0 0.110.0 --cache

# Step 4: Get code diff to see actual file changes
python3 -c "
from tagdiff.github import fetch_compare
import json
result = fetch_compare('tiangolo/fastapi', '0.100.0', '0.110.0')
print(json.dumps(result, indent=2))
"
```

Then read all four outputs and write your analysis. Reference specific version tags, commit SHAs, and changed files.

---

## What NOT To Use

| Flag              | Why Skip It                                                                                    |
| ----------------- | ---------------------------------------------------------------------------------------------- |
| `--structured`    | Calls an external LLM to parse changelogs. You ARE the LLM — parse them yourself.              |
| `--model`         | Selects which external LLM to use. Irrelevant when you're doing the analysis.                  |
| `tagdiff analyze` | The entire analyze command is an LLM wrapper. Use `search` + `diff` + `fetch_compare` instead. |

These flags require API keys you don't have and add cost/latency. The raw data is what you need.

---

## Environment

- **Binary location:** `/opt/homebrew/bin/tagdiff` (also available as `python3 -m tagdiff`)
- **GitHub token:** Set `GITHUB_TOKEN` env var if you hit rate limits (60 req/hr unauthenticated, 5000/hr authenticated)
- **Cache directory:** `~/.cache/tagdiff/` (auto-created)
- **Always use `--cache`** — avoids re-fetching on repeated queries within the same research session
