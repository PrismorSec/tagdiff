import argparse
import json
import sys

from tagdiff.core import get_changelog, search_changelogs, clear_cache, DEFAULT_CACHE_TTL


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
            # Truncate very long lines
            display = ml if len(ml) <= 120 else ml[:117] + "..."
            lines.append(f"    {display}")
        lines.append("")

    lines.append(f"  Total: {total} match(es) in {releases_matched} release(s)")
    lines.append("")
    return "\n".join(lines)


def _add_cache_args(parser):
    """Add common cache arguments to a parser."""
    parser.add_argument("--cache", action="store_true", help="Cache GitHub API responses locally (~/.cache/tagdiff)")
    parser.add_argument("--cache-ttl", type=int, default=DEFAULT_CACHE_TTL, help=f"Cache TTL in seconds (default: {DEFAULT_CACHE_TTL})")


def diff_main(args):
    try:
        result = get_changelog(
            args.repo,
            args.old_version,
            args.new_version,
            structured=args.structured,
            model=args.model,
            verbose=args.verbose,
            cache=args.cache,
            cache_ttl=args.cache_ttl,
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1

    formatted_result = json.dumps(result, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(formatted_result)
        if args.verbose:
            print(f"Result saved to {args.output}")
    else:
        print(formatted_result)

    return 0


def search_main(args):
    try:
        result = search_changelogs(
            args.repo,
            args.keyword,
            from_version=args.from_version,
            to_version=args.to_version,
            case_sensitive=args.case_sensitive,
            verbose=args.verbose,
            cache=args.cache,
            cache_ttl=args.cache_ttl,
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1

    if args.json:
        formatted = json.dumps(result, indent=2)
        if args.output:
            with open(args.output, "w") as f:
                f.write(formatted)
            if args.verbose:
                print(f"Result saved to {args.output}")
        else:
            print(formatted)
    else:
        text = format_search_results(result)
        if args.output:
            with open(args.output, "w") as f:
                f.write(text)
            if args.verbose:
                print(f"Result saved to {args.output}")
        else:
            print(text)

    return 0


def clear_cache_main(args):
    removed = clear_cache(repo=args.repo if args.repo else None)
    if args.repo:
        print(f"Cleared {removed} cached file(s) for {args.repo}")
    else:
        print(f"Cleared {removed} cached file(s)")
    return 0


def main():
    # Route based on first arg: "search", "clear-cache", or default diff
    cmd = sys.argv[1] if len(sys.argv) > 1 else None

    if cmd == "search":
        parser = argparse.ArgumentParser(
            prog="tagdiff search",
            description="Search changelogs by keyword across releases.",
        )
        parser.add_argument("_cmd", help=argparse.SUPPRESS)  # consume "search"
        parser.add_argument("repo", help="GitHub repo in owner/name format")
        parser.add_argument("keyword", help="Keyword or phrase to search for")
        parser.add_argument("--from", dest="from_version", default=None, help="Starting version tag (inclusive)")
        parser.add_argument("--to", dest="to_version", default=None, help="Ending version tag (inclusive)")
        parser.add_argument("--case-sensitive", action="store_true", help="Enable case-sensitive search")
        parser.add_argument("--json", action="store_true", help="Output results as JSON")
        parser.add_argument("--output", help="Save result to a file")
        parser.add_argument("--verbose", action="store_true", help="Show progress during execution")
        _add_cache_args(parser)
        args = parser.parse_args()
        return search_main(args)

    elif cmd == "clear-cache":
        parser = argparse.ArgumentParser(
            prog="tagdiff clear-cache",
            description="Clear cached GitHub API responses.",
        )
        parser.add_argument("_cmd", help=argparse.SUPPRESS)  # consume "clear-cache"
        parser.add_argument("repo", nargs="?", default=None, help="Clear cache for a specific repo only (optional)")
        args = parser.parse_args()
        return clear_cache_main(args)

    else:
        parser = argparse.ArgumentParser(
            prog="tagdiff",
            description="Compare GitHub release tags.",
        )
        parser.add_argument("repo", help="GitHub repo in owner/name format")
        parser.add_argument("old_version", help="Starting tag")
        parser.add_argument("new_version", help="Ending tag")
        parser.add_argument("--structured", action="store_true", help="Extract structured changelog using AI")
        parser.add_argument("--model", help="AI model to use (e.g. gpt-4o)")
        parser.add_argument("--output", help="Save result to a JSON file")
        parser.add_argument("--verbose", action="store_true", help="Show progress during execution")
        _add_cache_args(parser)
        args = parser.parse_args()
        return diff_main(args)


if __name__ == "__main__":
    sys.exit(main())
