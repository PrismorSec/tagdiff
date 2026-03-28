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
