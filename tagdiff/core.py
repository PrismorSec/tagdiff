import json
import os
import requests
from concurrent.futures import ThreadPoolExecutor

def fetch_releases(repo, stop_at_tag=None):
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


def get_changelog(repo, old_version, new_version, structured=False, model=None, verbose=False):
    releases = fetch_releases(repo, stop_at_tag=old_version)
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
