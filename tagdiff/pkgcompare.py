"""Compare GitHub releases/versions across two packages."""
from datetime import datetime, timezone

from tagdiff.config import DEFAULT_CACHE_TTL
from tagdiff.github import fetch_releases


def _parse_dt(iso_str):
    if not iso_str:
        return None
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))


def _release_map(releases):
    """Return {tag_name: release} dict."""
    return {r["tag_name"]: r for r in releases if r.get("tag_name")}


def _simplify_release(r):
    return {
        "tag": r.get("tag_name"),
        "name": r.get("name") or r.get("tag_name"),
        "published_at": r.get("published_at"),
        "prerelease": r.get("prerelease", False),
        "draft": r.get("draft", False),
        "url": r.get("html_url"),
    }


def compare_versions(repo1, repo2,
                     cache=False, cache_ttl=DEFAULT_CACHE_TTL, verbose=False):
    """Compare release versions between two GitHub repositories.

    Returns a structured comparison containing:
    - Versions present in both repos (exact tag match)
    - Versions only in repo1
    - Versions only in repo2
    - Release cadence stats (total, date span, avg days between releases)
    - Newest / oldest release per repo

    Args:
        repo1: First GitHub repo (``owner/name``).
        repo2: Second GitHub repo (``owner/name``).
        cache: Cache GitHub API responses.
        cache_ttl: Cache TTL in seconds.
        verbose: Print progress messages.

    Returns:
        Comparison dict.
    """
    releases1 = fetch_releases(repo1, cache=cache, cache_ttl=cache_ttl, verbose=verbose)
    releases2 = fetch_releases(repo2, cache=cache, cache_ttl=cache_ttl, verbose=verbose)

    if not releases1:
        raise ValueError(f"Could not fetch releases for repo: {repo1}")
    if not releases2:
        raise ValueError(f"Could not fetch releases for repo: {repo2}")

    map1 = _release_map(releases1)
    map2 = _release_map(releases2)

    tags1 = set(map1)
    tags2 = set(map2)

    common_tags = sorted(tags1 & tags2)
    only_tags1 = sorted(tags1 - tags2)
    only_tags2 = sorted(tags2 - tags1)

    def _cadence(releases):
        dates = sorted(
            [_parse_dt(r.get("published_at")) for r in releases if r.get("published_at")]
        )
        if not dates:
            return {"total": 0, "oldest": None, "newest": None, "avg_days_between_releases": None}
        span_days = (dates[-1] - dates[0]).days if len(dates) > 1 else 0
        avg = round(span_days / (len(dates) - 1), 1) if len(dates) > 1 else None
        return {
            "total": len(releases),
            "oldest": dates[0].isoformat(),
            "newest": dates[-1].isoformat(),
            "span_days": span_days,
            "avg_days_between_releases": avg,
        }

    def _common_detail(tag):
        r1 = map1[tag]
        r2 = map2[tag]
        dt1 = _parse_dt(r1.get("published_at"))
        dt2 = _parse_dt(r2.get("published_at"))
        days_apart = None
        if dt1 and dt2:
            days_apart = abs((dt1 - dt2).days)
        return {
            "tag": tag,
            "repo1_published_at": r1.get("published_at"),
            "repo2_published_at": r2.get("published_at"),
            "days_apart": days_apart,
        }

    common_detail = [_common_detail(t) for t in common_tags]

    return {
        "repos": [repo1, repo2],
        "repo1": {
            "repo": repo1,
            "cadence": _cadence(releases1),
            "releases": [_simplify_release(r) for r in releases1],
        },
        "repo2": {
            "repo": repo2,
            "cadence": _cadence(releases2),
            "releases": [_simplify_release(r) for r in releases2],
        },
        "comparison": {
            "common_tags": common_tags,
            "common_count": len(common_tags),
            "common_detail": common_detail,
            "only_in_repo1": [_simplify_release(map1[t]) for t in only_tags1],
            "only_in_repo1_count": len(only_tags1),
            "only_in_repo2": [_simplify_release(map2[t]) for t in only_tags2],
            "only_in_repo2_count": len(only_tags2),
        },
    }
