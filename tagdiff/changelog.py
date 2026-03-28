from concurrent.futures import ThreadPoolExecutor

from tagdiff.config import DEFAULT_CACHE_TTL
from tagdiff.github import fetch_releases
from tagdiff.llm import generate_structured_changelog


def get_changes_between_versions(releases, old_version, new_version, structured=False, model=None, verbose=False):
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

    changes = {}
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
        releases, old_version, new_version,
        structured=structured, model=model, verbose=verbose,
    )

    return {
        "repo": repo,
        "from": old_version,
        "to": new_version,
        "changes": changes,
    }
