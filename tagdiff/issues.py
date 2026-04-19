"""GitHub Issues fetching and comparison across repos/version ranges."""
from datetime import datetime, timezone

import requests

from tagdiff.cache import read_cache, write_cache
from tagdiff.config import DEFAULT_CACHE_TTL
from tagdiff.github import _auth_headers, fetch_releases
from tagdiff.releases import filter_by_range


def _parse_dt(iso_str):
    """Parse an ISO 8601 datetime string to a timezone-aware datetime."""
    if not iso_str:
        return None
    # GitHub always returns UTC with trailing Z
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))


def _release_dates_for_range(repo, from_version=None, to_version=None, cache=False, cache_ttl=DEFAULT_CACHE_TTL, verbose=False):
    """Return (since_dt, until_dt) based on the published_at of boundary releases."""
    releases = fetch_releases(repo, stop_at_tag=from_version, cache=cache, cache_ttl=cache_ttl, verbose=verbose)
    in_range = filter_by_range(releases, from_version=from_version, to_version=to_version)

    since_dt = None
    until_dt = None

    if in_range:
        # oldest release in range → since boundary
        since_dt = _parse_dt(in_range[0].get("published_at"))
        # newest release in range → until boundary
        until_dt = _parse_dt(in_range[-1].get("published_at"))

    return since_dt, until_dt


def fetch_issues(repo, state="all", since=None, until=None, labels=None,
                 cache=False, cache_ttl=DEFAULT_CACHE_TTL, verbose=False):
    """Fetch issues (excluding pull requests) for a GitHub repo.

    Args:
        repo: GitHub repo in ``owner/name`` format.
        state: ``"open"``, ``"closed"``, or ``"all"`` (default).
        since: Optional ISO 8601 string or datetime – only issues updated at/after this time.
        until: Optional ISO 8601 string or datetime – filter issues created before this time
               (post-fetch; GitHub API doesn't support an "until" param natively).
        labels: Comma-separated label string to filter by.
        cache: Whether to cache results locally.
        cache_ttl: Cache time-to-live in seconds.
        verbose: Print progress messages.

    Returns:
        List of simplified issue dicts.
    """
    cache_key = f"issues:{repo}:{state}:{since}:{until}:{labels}"

    if cache:
        cached = read_cache(repo, cache_key, ttl=cache_ttl)
        if cached is not None:
            if verbose:
                print(f"Using cached issues for {repo} ({len(cached)} issues)")
            return cached

    headers = _auth_headers()
    params = {"state": state, "per_page": 100}
    if labels:
        params["labels"] = labels

    # GitHub `since` filters by updated_at ≥ since
    if since:
        params["since"] = since if isinstance(since, str) else since.isoformat()

    issues = []
    page = 1

    while True:
        params["page"] = page
        url = f"https://api.github.com/repos/{repo}/issues"
        response = requests.get(url, headers=headers, params=params, timeout=30)

        if response.status_code != 200:
            if response.status_code == 403:
                raise ValueError("GitHub API rate limit exceeded. Use GITHUB_TOKEN to increase limits.")
            if response.status_code == 404:
                raise ValueError(f"Repository not found: {repo}")
            break

        data = response.json()
        if not data:
            break

        for item in data:
            # GitHub issues endpoint also returns PRs – skip them
            if "pull_request" in item:
                continue
            issues.append(_simplify_issue(item))

        page += 1
        if page > 10:
            break

    # Apply until filter (created_at ≤ until)
    if until:
        until_dt = until if isinstance(until, datetime) else _parse_dt(until)
        if until_dt is not None:
            issues = [
                i for i in issues
                if (dt := _parse_dt(i["created_at"])) is not None and dt <= until_dt
            ]

    if cache and issues:
        write_cache(repo, issues, cache_key)
        if verbose:
            print(f"Cached {len(issues)} issues for {repo}")

    return issues


def _simplify_issue(raw):
    """Extract the fields we care about from a raw GitHub issue dict."""
    return {
        "number": raw["number"],
        "title": raw["title"],
        "state": raw["state"],
        "created_at": raw.get("created_at"),
        "updated_at": raw.get("updated_at"),
        "closed_at": raw.get("closed_at"),
        "author": raw.get("user", {}).get("login"),
        "labels": [lbl["name"] for lbl in raw.get("labels", [])],
        "url": raw.get("html_url"),
        "comments": raw.get("comments", 0),
    }


def get_issues_for_version_range(repo, from_version=None, to_version=None,
                                  state="all", labels=None,
                                  cache=False, cache_ttl=DEFAULT_CACHE_TTL, verbose=False):
    """Fetch GitHub issues that fall within a version range (based on release dates).

    Args:
        repo: GitHub repo in ``owner/name`` format.
        from_version: Start version tag (inclusive). Uses the release's published_at as the lower bound.
        to_version: End version tag (inclusive). Uses the release's published_at as the upper bound.
        state: Issue state filter – ``"open"``, ``"closed"``, or ``"all"``.
        labels: Comma-separated label string to filter by.
        cache: Cache GitHub API responses.
        cache_ttl: Cache TTL in seconds.
        verbose: Print progress messages.

    Returns:
        Dict with repo, version range, and list of issues.
    """
    since_dt, until_dt = _release_dates_for_range(
        repo, from_version=from_version, to_version=to_version,
        cache=cache, cache_ttl=cache_ttl, verbose=verbose,
    )

    if verbose and since_dt:
        print(f"Fetching issues from {since_dt.isoformat()} to {until_dt.isoformat() if until_dt else 'now'}")

    issues = fetch_issues(
        repo, state=state, since=since_dt, until=until_dt,
        labels=labels, cache=cache, cache_ttl=cache_ttl, verbose=verbose,
    )

    # Further narrow: only issues *created* within the range
    if since_dt:
        issues = [
            i for i in issues
            if (dt := _parse_dt(i["created_at"])) is not None and dt >= since_dt
        ]

    return {
        "repo": repo,
        "from_version": from_version,
        "to_version": to_version,
        "since": since_dt.isoformat() if since_dt else None,
        "until": until_dt.isoformat() if until_dt else None,
        "state": state,
        "total": len(issues),
        "issues": issues,
    }


def compare_issues(repo1, repo2,
                   from_version1=None, to_version1=None,
                   from_version2=None, to_version2=None,
                   state="all", labels=None,
                   cache=False, cache_ttl=DEFAULT_CACHE_TTL, verbose=False):
    """Compare GitHub issues between two repos over (optionally different) version ranges.

    Produces a side-by-side comparison with:
    - Issue counts and breakdowns per repo
    - Issues unique to each repo (matched by title similarity)
    - Common issue titles present in both
    - Label distribution comparison

    Args:
        repo1: First GitHub repo (``owner/name``).
        repo2: Second GitHub repo (``owner/name``).
        from_version1: Start version for repo1.
        to_version1: End version for repo1.
        from_version2: Start version for repo2.
        to_version2: End version for repo2.
        state: Issue state filter.
        labels: Comma-separated label filter.
        cache: Cache API responses.
        cache_ttl: Cache TTL in seconds.
        verbose: Print progress.

    Returns:
        Comparison dict.
    """
    result1 = get_issues_for_version_range(
        repo1, from_version=from_version1, to_version=to_version1,
        state=state, labels=labels, cache=cache, cache_ttl=cache_ttl, verbose=verbose,
    )
    result2 = get_issues_for_version_range(
        repo2, from_version=from_version2, to_version=to_version2,
        state=state, labels=labels, cache=cache, cache_ttl=cache_ttl, verbose=verbose,
    )

    titles1 = {i["title"].lower().strip() for i in result1["issues"]}
    titles2 = {i["title"].lower().strip() for i in result2["issues"]}

    common_titles = titles1 & titles2
    only_in_1 = [i for i in result1["issues"] if i["title"].lower().strip() not in titles2]
    only_in_2 = [i for i in result2["issues"] if i["title"].lower().strip() not in titles1]
    common_in_1 = [i for i in result1["issues"] if i["title"].lower().strip() in common_titles]
    common_in_2 = [i for i in result2["issues"] if i["title"].lower().strip() in common_titles]

    def _label_dist(issues):
        dist = {}
        for issue in issues:
            for lbl in issue.get("labels", []):
                dist[lbl] = dist.get(lbl, 0) + 1
        return dict(sorted(dist.items(), key=lambda x: x[1], reverse=True))

    def _state_counts(issues):
        return {
            "open": sum(1 for i in issues if i["state"] == "open"),
            "closed": sum(1 for i in issues if i["state"] == "closed"),
        }

    return {
        "repos": [repo1, repo2],
        "repo1": {
            "repo": repo1,
            "from_version": from_version1,
            "to_version": to_version1,
            "since": result1["since"],
            "until": result1["until"],
            "total": result1["total"],
            "state_counts": _state_counts(result1["issues"]),
            "label_distribution": _label_dist(result1["issues"]),
            "issues": result1["issues"],
        },
        "repo2": {
            "repo": repo2,
            "from_version": from_version2,
            "to_version": to_version2,
            "since": result2["since"],
            "until": result2["until"],
            "total": result2["total"],
            "state_counts": _state_counts(result2["issues"]),
            "label_distribution": _label_dist(result2["issues"]),
            "issues": result2["issues"],
        },
        "comparison": {
            "common_titles": sorted(common_titles),
            "common_count": len(common_titles),
            "only_in_repo1": only_in_1,
            "only_in_repo1_count": len(only_in_1),
            "only_in_repo2": only_in_2,
            "only_in_repo2_count": len(only_in_2),
            "common_in_repo1": common_in_1,
            "common_in_repo2": common_in_2,
        },
    }
