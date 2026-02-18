import json
import requests

def fetch_releases(repo, stop_at_tag=None):
    releases = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repo}/releases?page={page}&per_page=100"
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
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
            
    return releases


def get_changes_between_versions(releases, old_version, new_version, structured=False):
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
            change_data = {
                "published_at": published_at,
                "changelog": changelog,
            }
            if structured and changelog and changelog.strip():
                structured_data = generate_structured_changelog(changelog)
                if structured_data:
                    change_data["structured_changelog"] = structured_data
            
            changes[tag] = change_data

    return changes


def get_changelog(repo, old_version, new_version, structured=False):
    releases = fetch_releases(repo, stop_at_tag=old_version)
    if not releases:
        raise ValueError("Could not fetch releases")

    changes = get_changes_between_versions(releases, old_version, new_version, structured=structured)

    return {
        "repo": repo,
        "from": old_version,
        "to": new_version,
        "changes": changes,
    }


def generate_structured_changelog(changelog_text):
    try:
        from litellm import completion
    except ImportError:
        return None

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

    import os
    model = os.getenv("TAGDIFF_MODEL", "gpt-3.5-turbo")

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
        # Fallback or error logging could go here
        return {"error": str(e)}
