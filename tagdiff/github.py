import os
import requests

from tagdiff.cache import read_cache, write_cache
from tagdiff.config import DEFAULT_CACHE_TTL


def _auth_headers():
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return {"Authorization": f"token {token}"}
    return {}


def fetch_releases(repo, stop_at_tag=None, cache=False, cache_ttl=DEFAULT_CACHE_TTL, verbose=False):
    if cache:
        cached = read_cache(repo, stop_at_tag, ttl=cache_ttl)
        if cached is not None:
            if verbose:
                print(f"Using cached releases for {repo} ({len(cached)} releases)")
            return cached

    headers = _auth_headers()
    releases = []
    page = 1

    while True:
        url = f"https://api.github.com/repos/{repo}/releases?page={page}&per_page=100"
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            if response.status_code == 403:
                raise ValueError("GitHub API rate limit exceeded. Use GITHUB_TOKEN to increase limits.")
            if response.status_code == 404:
                raise ValueError(f"Repository not found: {repo}")
            if page == 1:
                raise ValueError(
                    f"GitHub API returned {response.status_code} for {repo}: {response.text[:200]}"
                )
            break

        data = response.json()
        if not data:
            break

        releases.extend(data)

        if stop_at_tag:
            found = any(r.get("tag_name") == stop_at_tag for r in data)
            if found:
                break

        page += 1
        if page > 10:
            break

    if cache and releases:
        write_cache(repo, releases, stop_at_tag)
        if verbose:
            print(f"Cached {len(releases)} releases for {repo}")

    return releases


def fetch_compare(repo, base, head, verbose=False):
    """Fetch GitHub compare API between two refs. Returns commit summaries and changed files."""
    headers = _auth_headers()
    url = f"https://api.github.com/repos/{repo}/compare/{base}...{head}"

    if verbose:
        print(f"  Fetching diff: {base}...{head}")

    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        return None

    data = response.json()
    commits = [
        {
            "sha": c["sha"][:7],
            "message": c["commit"]["message"].split("\n")[0],
            "author": c["commit"]["author"]["name"],
        }
        for c in data.get("commits", [])
    ]

    files = [
        {
            "filename": f["filename"],
            "status": f["status"],
            "additions": f["additions"],
            "deletions": f["deletions"],
        }
        for f in data.get("files", [])
    ]

    return {
        "total_commits": len(commits),
        "commits": commits,
        "total_files_changed": len(files),
        "files": files,
    }
