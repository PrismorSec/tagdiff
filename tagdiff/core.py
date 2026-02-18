import requests


def fetch_releases(repo):
    url = f"https://api.github.com/repos/{repo}/releases"
    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        return None
    return response.json()


def get_changes_between_versions(releases, old_version, new_version):
    changes = {}
    ordered_releases = list(reversed(releases))

    collecting = False
    for release in ordered_releases:
        tag = release.get("tag_name")
        published_at = release.get("published_at")
        changelog = release.get("body")

        if tag == old_version:
            collecting = True
            continue

        if tag == new_version:
            break

        if collecting:
            changes[tag] = {
                "published_at": published_at,
                "changelog": changelog,
            }

    return changes


def get_changelog(repo, old_version, new_version):
    releases = fetch_releases(repo)
    if releases is None:
        raise ValueError("Could not fetch releases")

    changes = get_changes_between_versions(releases, old_version, new_version)

    return {
        "repo": repo,
        "from": old_version,
        "to": new_version,
        "changes": changes,
    }
