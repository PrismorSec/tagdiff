from tagdiff.config import DEFAULT_CACHE_TTL
from tagdiff.github import fetch_releases, fetch_compare
from tagdiff.llm import stream_analysis
from tagdiff.releases import filter_by_range

ANALYSIS_SYSTEM_PROMPT = """You are an expert software analyst. The user will give you a question about changes
in a GitHub repository between specific versions. You have access to the release changelogs
and optionally the code diff (commits + changed files).

Your job is to deeply analyze the data and give a thorough, structured answer to the user's question.

Structure your response as:
1. **Summary** - A concise answer to the question (2-3 sentences)
2. **Detailed Analysis** - Walk through the relevant changes version by version
3. **Key Findings** - Bullet points of the most important discoveries
4. **Impact Assessment** - What these changes mean for users of the library (breaking changes, migration notes, etc.)

Be specific. Reference exact version tags and changelog entries. If the data doesn't contain enough
information to fully answer the question, say so clearly."""


def _print_step(step_num, msg):
    print(f"\n  [{step_num}] {msg}")


def _collect_changelogs(filtered):
    parts = []
    for r in filtered:
        tag = r.get("tag_name", "unknown")
        date = (r.get("published_at") or "")[:10]
        body = r.get("body") or "(no changelog)"
        parts.append(f"### {tag} ({date})\n{body}")
    text = "\n\n".join(parts)
    if len(text) > 60000:
        text = text[:60000] + "\n\n... (truncated)"
    return parts, text


def _build_diff_context(compare, tag_from, tag_to):
    lines = [f"Code diff: {tag_from}...{tag_to}"]
    lines.append(f"Total commits: {compare['total_commits']}")
    lines.append(f"Files changed: {compare['total_files_changed']}")
    lines.append("")
    lines.append("Commits:")
    for c in compare["commits"][:50]:
        lines.append(f"  {c['sha']} {c['message']} ({c['author']})")
    lines.append("")
    lines.append("Changed files:")
    for f in compare["files"][:100]:
        lines.append(f"  {f['status']:>10} {f['filename']} (+{f['additions']}/-{f['deletions']})")
    text = "\n".join(lines)
    if len(text) > 30000:
        text = text[:30000] + "\n\n... (truncated)"
    return text


def analyze_changelog(repo, query, from_version=None, to_version=None, model=None,
                      with_diff=False, cache=False, cache_ttl=DEFAULT_CACHE_TTL, verbose=False):
    """
    Agentic deep-research: gathers changelogs (and optionally code diffs) across a version range,
    then uses an LLM to answer a specific question about what changed and why.
    """
    try:
        from litellm import completion  # noqa: F401 — validate availability early
    except ImportError:
        raise ValueError("litellm package is required for analyze. Install with: pip install litellm")

    if not model:
        from tagdiff.config import DEFAULT_MODEL
        model = DEFAULT_MODEL

    # Step 1: Fetch releases
    _print_step(1, f"Fetching releases for {repo}...")
    stop_tag = from_version if from_version else None
    releases = fetch_releases(repo, stop_at_tag=stop_tag, cache=cache, cache_ttl=cache_ttl, verbose=verbose)
    if not releases:
        raise ValueError(f"Could not fetch releases for repo: {repo}")

    filtered = filter_by_range(releases, from_version, to_version)
    tags = [r.get("tag_name") for r in filtered]
    print(f"       Found {len(filtered)} releases: {tags[0] if tags else '?'} -> {tags[-1] if tags else '?'}")

    # Step 2: Collect changelogs
    _print_step(2, "Collecting changelogs...")
    changelog_parts, full_changelog = _collect_changelogs(filtered)
    print(f"       Collected {len(changelog_parts)} changelogs ({len(full_changelog)} chars)")

    # Step 3: Optionally fetch code diff
    diff_context = ""
    if with_diff and len(tags) >= 2:
        _print_step(3, "Fetching code diff from GitHub...")
        compare = fetch_compare(repo, tags[0], tags[-1], verbose=verbose)
        if compare:
            diff_context = _build_diff_context(compare, tags[0], tags[-1])
            print(f"       {compare['total_commits']} commits, {compare['total_files_changed']} files changed")
        else:
            print("       Could not fetch compare diff (tags may not exist as git refs)")
        step_num = 4
    else:
        step_num = 3

    # Step N: LLM analysis
    _print_step(step_num, f"Analyzing with {model}...")

    user_content = f"""Question: {query}

Repository: {repo}
Version range: {tags[0] if tags else '?'} -> {tags[-1] if tags else '?'}

## Release Changelogs

{full_changelog}"""

    if diff_context:
        user_content += f"\n\n## Code Diff\n\n{diff_context}"

    try:
        analysis_text = stream_analysis(ANALYSIS_SYSTEM_PROMPT, user_content, model=model)
    except Exception as e:
        analysis_text = f"LLM analysis failed: {e}"
        print(f"\n       Error: {e}")

    return {
        "repo": repo,
        "query": query,
        "from": from_version or "(earliest)",
        "to": to_version or "(latest)",
        "releases_analyzed": len(filtered),
        "model": model,
        "with_diff": with_diff,
        "analysis": analysis_text,
    }
