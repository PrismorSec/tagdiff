def format_issues_result(result):
    """Format a get_issues_for_version_range result as readable CLI output."""
    lines = []
    repo = result["repo"]
    from_v = result.get("from_version") or "earliest"
    to_v = result.get("to_version") or "latest"
    total = result["total"]
    state = result.get("state", "all")

    lines.append("")
    lines.append(f"  Issues for {repo}  ({from_v} -> {to_v})  state={state}")
    if result.get("since"):
        lines.append(f"  Date range: {result['since'][:10]} to {result['until'][:10] if result.get('until') else 'now'}")
    lines.append(f"  Total: {total} issue(s)")
    lines.append("")

    if not result["issues"]:
        lines.append("  No issues found.")
        lines.append("")
        return "\n".join(lines)

    for issue in result["issues"]:
        state_str = f"[{issue['state']}]"
        labels = f"  labels: {', '.join(issue['labels'])}" if issue["labels"] else ""
        date = issue["created_at"][:10] if issue["created_at"] else "unknown"
        lines.append(f"  #{issue['number']}  {state_str}  {date}  {issue['title']}{labels}")

    lines.append("")
    return "\n".join(lines)


def format_compare_issues(result):
    """Format a compare_issues result as readable CLI output."""
    lines = []
    repo1, repo2 = result["repos"]
    r1 = result["repo1"]
    r2 = result["repo2"]
    cmp = result["comparison"]

    lines.append("")
    lines.append(f"  Issue Comparison:  {repo1}  vs  {repo2}")
    lines.append("")
    lines.append(f"  {repo1}: {r1['total']} issue(s)  "
                 f"(open={r1['state_counts']['open']}, closed={r1['state_counts']['closed']})")
    if r1.get("since"):
        lines.append(f"    range: {r1['since'][:10]} to {r1['until'][:10] if r1.get('until') else 'now'}  "
                     f"({r1.get('from_version', '?')} -> {r1.get('to_version', '?')})")
    lines.append(f"  {repo2}: {r2['total']} issue(s)  "
                 f"(open={r2['state_counts']['open']}, closed={r2['state_counts']['closed']})")
    if r2.get("since"):
        lines.append(f"    range: {r2['since'][:10]} to {r2['until'][:10] if r2.get('until') else 'now'}  "
                     f"({r2.get('from_version', '?')} -> {r2.get('to_version', '?')})")

    lines.append("")
    lines.append(f"  Common titles:     {cmp['common_count']}")
    lines.append(f"  Only in {repo1}: {cmp['only_in_repo1_count']}")
    lines.append(f"  Only in {repo2}: {cmp['only_in_repo2_count']}")

    if cmp["only_in_repo1"]:
        lines.append("")
        lines.append(f"  Issues only in {repo1}:")
        lines.append(f"  {'─' * 50}")
        for i in cmp["only_in_repo1"]:
            lines.append(f"    #{i['number']}  [{i['state']}]  {i['title']}")

    if cmp["only_in_repo2"]:
        lines.append("")
        lines.append(f"  Issues only in {repo2}:")
        lines.append(f"  {'─' * 50}")
        for i in cmp["only_in_repo2"]:
            lines.append(f"    #{i['number']}  [{i['state']}]  {i['title']}")

    if cmp["common_titles"]:
        lines.append("")
        lines.append("  Common issue titles:")
        lines.append(f"  {'─' * 50}")
        for title in cmp["common_titles"]:
            lines.append(f"    - {title}")

    lines.append("")
    return "\n".join(lines)


def format_compare_versions(result):
    """Format a compare_versions result as readable CLI output."""
    lines = []
    repo1, repo2 = result["repos"]
    r1 = result["repo1"]
    r2 = result["repo2"]
    cmp = result["comparison"]

    lines.append("")
    lines.append(f"  Version Comparison:  {repo1}  vs  {repo2}")
    lines.append("")

    c1 = r1["cadence"]
    c2 = r2["cadence"]
    lines.append(f"  {repo1}:")
    lines.append(f"    Total releases:  {c1['total']}")
    if c1.get("newest"):
        lines.append(f"    Newest:          {c1['newest'][:10]}")
        lines.append(f"    Oldest:          {c1['oldest'][:10]}")
    if c1.get("avg_days_between_releases") is not None:
        lines.append(f"    Avg release gap: {c1['avg_days_between_releases']} days")

    lines.append("")
    lines.append(f"  {repo2}:")
    lines.append(f"    Total releases:  {c2['total']}")
    if c2.get("newest"):
        lines.append(f"    Newest:          {c2['newest'][:10]}")
        lines.append(f"    Oldest:          {c2['oldest'][:10]}")
    if c2.get("avg_days_between_releases") is not None:
        lines.append(f"    Avg release gap: {c2['avg_days_between_releases']} days")

    lines.append("")
    lines.append(f"  Common tags ({cmp['common_count']}):")
    if cmp["common_detail"]:
        lines.append(f"  {'─' * 50}")
        for entry in cmp["common_detail"]:
            apart = f"  {entry['days_apart']}d apart" if entry.get("days_apart") is not None else ""
            lines.append(f"    {entry['tag']}{apart}")

    if cmp["only_in_repo1"]:
        lines.append("")
        lines.append(f"  Only in {repo1} ({cmp['only_in_repo1_count']}):")
        lines.append(f"  {'─' * 50}")
        for r in cmp["only_in_repo1"]:
            date = r["published_at"][:10] if r.get("published_at") else "unknown"
            lines.append(f"    {r['tag']}  ({date})")

    if cmp["only_in_repo2"]:
        lines.append("")
        lines.append(f"  Only in {repo2} ({cmp['only_in_repo2_count']}):")
        lines.append(f"  {'─' * 50}")
        for r in cmp["only_in_repo2"]:
            date = r["published_at"][:10] if r.get("published_at") else "unknown"
            lines.append(f"    {r['tag']}  ({date})")

    lines.append("")
    return "\n".join(lines)


def format_search_results(result):
    """Format search results as a readable CLI table."""
    lines = []
    repo = result["repo"]
    keyword = result["keyword"]
    from_v = result["from"]
    to_v = result["to"]
    total = result["total_matches"]
    releases_matched = result["releases_matched"]
    releases_searched = result["releases_searched"]

    lines.append("")
    lines.append(f"  Search: \"{keyword}\" in {repo} ({from_v} -> {to_v})")
    lines.append(f"  Searched {releases_searched} releases, found {total} match(es) across {releases_matched} release(s)")
    lines.append("")

    if not result["matches"]:
        lines.append("  No matches found.")
        lines.append("")
        return "\n".join(lines)

    for m in result["matches"]:
        tag = m["tag"]
        date = m["published_at"][:10] if m["published_at"] else "unknown"
        count = m["match_count"]

        lines.append(f"  {tag}  ({date})  [{count} match(es)]")
        lines.append(f"  {'─' * 50}")
        for ml in m["matching_lines"]:
            display = ml if len(ml) <= 120 else ml[:117] + "..."
            lines.append(f"    {display}")
        lines.append("")

    lines.append(f"  Total: {total} match(es) in {releases_matched} release(s)")
    lines.append("")
    return "\n".join(lines)
