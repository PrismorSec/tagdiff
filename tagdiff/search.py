from tagdiff.config import DEFAULT_CACHE_TTL
from tagdiff.github import fetch_releases
from tagdiff.releases import filter_by_range


def search_changelogs(repo, keyword, from_version=None, to_version=None, case_sensitive=False, verbose=False, cache=False, cache_ttl=DEFAULT_CACHE_TTL):
    stop_tag = from_version if from_version else None
    releases = fetch_releases(repo, stop_at_tag=stop_tag, cache=cache, cache_ttl=cache_ttl, verbose=verbose)
    if not releases:
        raise ValueError(f"Could not fetch releases for repo: {repo}")

    filtered = filter_by_range(releases, from_version, to_version)

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

    return {
        "repo": repo,
        "keyword": keyword,
        "from": from_version or "(earliest)",
        "to": to_version or "(latest)",
        "total_matches": sum(m["match_count"] for m in matches),
        "releases_matched": len(matches),
        "releases_searched": len(filtered),
        "matches": matches,
    }
