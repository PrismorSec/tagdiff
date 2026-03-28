import argparse
import json
import sys

from tagdiff.changelog import get_changelog
from tagdiff.search import search_changelogs
from tagdiff.analyze import analyze_changelog
from tagdiff.cache import clear_cache
from tagdiff.config import DEFAULT_CACHE_TTL
from tagdiff.formatter import format_search_results


def _add_cache_args(parser):
    parser.add_argument("--cache", action="store_true", help="Cache GitHub API responses locally (~/.cache/tagdiff)")
    parser.add_argument("--cache-ttl", type=int, default=DEFAULT_CACHE_TTL, help=f"Cache TTL in seconds (default: {DEFAULT_CACHE_TTL})")


def _output_result(result_text, args, verbose_msg=None):
    if args.output:
        with open(args.output, "w") as f:
            f.write(result_text)
        if hasattr(args, "verbose") and args.verbose and verbose_msg:
            print(verbose_msg)
    else:
        print(result_text)


def diff_main(args):
    try:
        result = get_changelog(
            args.repo, args.old_version, args.new_version,
            structured=args.structured, model=args.model,
            verbose=args.verbose, cache=args.cache, cache_ttl=args.cache_ttl,
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1

    _output_result(json.dumps(result, indent=2), args, f"Result saved to {args.output}")
    return 0


def search_main(args):
    try:
        result = search_changelogs(
            args.repo, args.keyword,
            from_version=args.from_version, to_version=args.to_version,
            case_sensitive=args.case_sensitive, verbose=args.verbose,
            cache=args.cache, cache_ttl=args.cache_ttl,
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1

    if args.json:
        _output_result(json.dumps(result, indent=2), args, f"Result saved to {args.output}")
    else:
        _output_result(format_search_results(result), args, f"Result saved to {args.output}")
    return 0


def analyze_main(args):
    try:
        result = analyze_changelog(
            args.repo, args.query,
            from_version=args.from_version, to_version=args.to_version,
            model=args.model, with_diff=args.with_diff,
            cache=args.cache, cache_ttl=args.cache_ttl,
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1

    if args.json:
        print(json.dumps(result, indent=2))

    if args.output:
        with open(args.output, "w") as f:
            f.write(json.dumps(result, indent=2) if args.json else result["analysis"])
        print(f"\n  Result saved to {args.output}")

    return 0


def clear_cache_main(args):
    removed = clear_cache(repo=args.repo if args.repo else None)
    if args.repo:
        print(f"Cleared {removed} cached file(s) for {args.repo}")
    else:
        print(f"Cleared {removed} cached file(s)")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else None

    if cmd == "search":
        parser = argparse.ArgumentParser(prog="tagdiff search", description="Search changelogs by keyword across releases.")
        parser.add_argument("_cmd", help=argparse.SUPPRESS)
        parser.add_argument("repo", help="GitHub repo in owner/name format")
        parser.add_argument("keyword", help="Keyword or phrase to search for")
        parser.add_argument("--from", dest="from_version", default=None, help="Starting version tag (inclusive)")
        parser.add_argument("--to", dest="to_version", default=None, help="Ending version tag (inclusive)")
        parser.add_argument("--case-sensitive", action="store_true", help="Enable case-sensitive search")
        parser.add_argument("--json", action="store_true", help="Output results as JSON")
        parser.add_argument("--output", help="Save result to a file")
        parser.add_argument("--verbose", action="store_true", help="Show progress during execution")
        _add_cache_args(parser)
        return search_main(parser.parse_args())

    elif cmd == "analyze":
        parser = argparse.ArgumentParser(prog="tagdiff analyze", description="Deep research: AI-powered analysis of changelogs and code diffs.")
        parser.add_argument("_cmd", help=argparse.SUPPRESS)
        parser.add_argument("repo", help="GitHub repo in owner/name format")
        parser.add_argument("query", help="Question to research (e.g. 'How did auth change?')")
        parser.add_argument("--from", dest="from_version", default=None, help="Starting version tag (inclusive)")
        parser.add_argument("--to", dest="to_version", default=None, help="Ending version tag (inclusive)")
        parser.add_argument("--with-diff", action="store_true", help="Also fetch GitHub code diff (commits + changed files)")
        parser.add_argument("--model", help="AI model to use for analysis")
        parser.add_argument("--json", action="store_true", help="Also output full result as JSON")
        parser.add_argument("--output", help="Save analysis to a file")
        _add_cache_args(parser)
        return analyze_main(parser.parse_args())

    elif cmd == "clear-cache":
        parser = argparse.ArgumentParser(prog="tagdiff clear-cache", description="Clear cached GitHub API responses.")
        parser.add_argument("_cmd", help=argparse.SUPPRESS)
        parser.add_argument("repo", nargs="?", default=None, help="Clear cache for a specific repo only (optional)")
        return clear_cache_main(parser.parse_args())

    else:
        parser = argparse.ArgumentParser(prog="tagdiff", description="Compare GitHub release tags.")
        parser.add_argument("repo", help="GitHub repo in owner/name format")
        parser.add_argument("old_version", help="Starting tag")
        parser.add_argument("new_version", help="Ending tag")
        parser.add_argument("--structured", action="store_true", help="Extract structured changelog using AI")
        parser.add_argument("--model", help="AI model to use (e.g. gpt-5-nano)")
        parser.add_argument("--output", help="Save result to a JSON file")
        parser.add_argument("--verbose", action="store_true", help="Show progress during execution")
        _add_cache_args(parser)
        return diff_main(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
