import hashlib
import json
import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CACHE_DIR = Path(os.getenv("TAGDIFF_CACHE_DIR", Path.home() / ".cache" / "tagdiff"))
DEFAULT_CACHE_TTL = 3600  # 1 hour


def _cache_path(repo, stop_at_tag=None):
    key = repo
    if stop_at_tag:
        key += f":{stop_at_tag}"
    filename = hashlib.sha256(key.encode()).hexdigest()[:16] + ".json"
    return CACHE_DIR / filename


def _read_cache(repo, stop_at_tag=None, ttl=DEFAULT_CACHE_TTL):
    path = _cache_path(repo, stop_at_tag)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if time.time() - data.get("cached_at", 0) > ttl:
            return None
        return data["releases"]
    except (json.JSONDecodeError, KeyError):
        return None


def _write_cache(repo, releases, stop_at_tag=None):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(repo, stop_at_tag)
    data = {
        "repo": repo,
        "stop_at_tag": stop_at_tag,
        "cached_at": time.time(),
        "releases": releases,
    }
    path.write_text(json.dumps(data))


def clear_cache(repo=None):
    """Clear cached releases. If repo is given, clear only that repo's cache. Otherwise clear all."""
    if not CACHE_DIR.exists():
        return 0
    removed = 0
    if repo:
        for path in CACHE_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                if data.get("repo") == repo:
                    path.unlink()
                    removed += 1
            except (json.JSONDecodeError, KeyError):
                pass
    else:
        for path in CACHE_DIR.glob("*.json"):
            path.unlink()
            removed += 1
    return removed


def fetch_releases(repo, stop_at_tag=None, cache=False, cache_ttl=DEFAULT_CACHE_TTL, verbose=False):
    if cache:
        cached = _read_cache(repo, stop_at_tag, ttl=cache_ttl)
        if cached is not None:
            if verbose:
                print(f"Using cached releases for {repo} ({len(cached)} releases)")
            return cached

    token = os.getenv("GITHUB_TOKEN")
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"

    releases = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repo}/releases?page={page}&per_page=100"
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            if response.status_code == 403:
                raise ValueError("GitHub API rate limit exceeded. Use GITHUB_TOKEN to increase limits.")
            break

        data = response.json()
        if not data:
            break

        releases.extend(data)

        # Check if we found the stop_at_tag
        if stop_at_tag:
            found = any(r.get("tag_name") == stop_at_tag for r in data)
            if found:
                break

        page += 1
        if page > 10: # Safety limit
            break

    if cache and releases:
        _write_cache(repo, releases, stop_at_tag)
        if verbose:
            print(f"Cached {len(releases)} releases for {repo}")

    return releases


def get_changes_between_versions(releases, old_version, new_version, structured=False, model=None, verbose=False):
    changes = {}
    ordered_releases = list(reversed(releases))

    to_process = []
    collecting = False
    for release in ordered_releases:
        tag = release.get("tag_name")
        if tag == old_version:
            collecting = True
            continue

        if tag == new_version:
            break

        if collecting:
            to_process.append(release)

    def process_release(release):
        tag = release.get("tag_name")
        published_at = release.get("published_at")
        changelog = release.get("body")
        
        if verbose:
            print(f"Processing {tag}...")

        change_data = {
            "published_at": published_at,
            "changelog": changelog,
        }
        
        if structured and changelog and changelog.strip():
            structured_data = generate_structured_changelog(changelog, model=model)
            if structured_data:
                change_data["structured_changelog"] = structured_data
        
        return tag, change_data

    # Parallelize LLM calls
    if structured and to_process:
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(process_release, to_process))
            for tag, data in results:
                changes[tag] = data
    else:
        for release in to_process:
            tag, data = process_release(release)
            changes[tag] = data

    return changes


def get_changelog(repo, old_version, new_version, structured=False, model=None, verbose=False, cache=False, cache_ttl=DEFAULT_CACHE_TTL):
    releases = fetch_releases(repo, stop_at_tag=old_version, cache=cache, cache_ttl=cache_ttl, verbose=verbose)
    if not releases:
        raise ValueError(f"Could not fetch releases for repo: {repo}")

    changes = get_changes_between_versions(
        releases, 
        old_version, 
        new_version, 
        structured=structured, 
        model=model,
        verbose=verbose
    )

    return {
        "repo": repo,
        "from": old_version,
        "to": new_version,
        "changes": changes,
    }


def search_changelogs(repo, keyword, from_version=None, to_version=None, case_sensitive=False, verbose=False, cache=False, cache_ttl=DEFAULT_CACHE_TTL):
    stop_tag = from_version if from_version else None
    releases = fetch_releases(repo, stop_at_tag=stop_tag, cache=cache, cache_ttl=cache_ttl, verbose=verbose)
    if not releases:
        raise ValueError(f"Could not fetch releases for repo: {repo}")

    ordered = list(reversed(releases))

    # Determine the slice of releases to search
    if from_version and to_version:
        collecting = False
        filtered = []
        for r in ordered:
            tag = r.get("tag_name")
            if tag == from_version:
                collecting = True
                filtered.append(r)
                continue
            if tag == to_version:
                filtered.append(r)
                break
            if collecting:
                filtered.append(r)
    elif from_version:
        collecting = False
        filtered = []
        for r in ordered:
            tag = r.get("tag_name")
            if tag == from_version:
                collecting = True
            if collecting:
                filtered.append(r)
    elif to_version:
        filtered = []
        for r in ordered:
            tag = r.get("tag_name")
            filtered.append(r)
            if tag == to_version:
                break
    else:
        filtered = ordered

    if verbose:
        print(f"Searching {len(filtered)} releases for '{keyword}'...")

    kw = keyword if case_sensitive else keyword.lower()
    matches = []
    for release in filtered:
        tag = release.get("tag_name", "")
        body = release.get("body") or ""
        published_at = release.get("published_at", "")

        search_body = body if case_sensitive else body.lower()
        if kw not in search_body:
            continue

        # Extract matching lines with context
        matching_lines = []
        for line in body.splitlines():
            search_line = line if case_sensitive else line.lower()
            if kw in search_line:
                matching_lines.append(line.strip())

        matches.append({
            "tag": tag,
            "published_at": published_at,
            "matching_lines": matching_lines,
            "match_count": len(matching_lines),
        })

    from_label = from_version or "(earliest)"
    to_label = to_version or "(latest)"

    return {
        "repo": repo,
        "keyword": keyword,
        "from": from_label,
        "to": to_label,
        "total_matches": sum(m["match_count"] for m in matches),
        "releases_matched": len(matches),
        "releases_searched": len(filtered),
        "matches": matches,
    }


def generate_structured_changelog(changelog_text, model=None):
    try:
        from litellm import completion
    except ImportError:
        return {"error": "litellm package missing. Install it with 'pip install litellm'"}

    prompt = """
    You are a changelog assistant.
    Extract the following from the changelog text:
    - breaking_changes (list of strings)
    - features (list of strings)
    - fixes (list of strings)
    - deprecations (list of strings)
    - other (list of strings)

    Return ONLY JSON. Do not use markdown blocks.
    """

    if not model:
        model = os.getenv("TAGDIFF_MODEL", "gpt-4o-mini")

    try:
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": changelog_text}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        return {"error": str(e)}
