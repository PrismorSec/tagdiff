import argparse
import json
import sys

from tagdiff.core import get_changelog


def main():
    parser = argparse.ArgumentParser(description="Compare GitHub release tags.")
    parser.add_argument("repo", help="GitHub repo in owner/name format")
    parser.add_argument("old_version", help="Starting tag")
    parser.add_argument("new_version", help="Ending tag")
    parser.add_argument("--structured", action="store_true", help="Extract structured changelog using AI")
    args = parser.parse_args()

    try:
        result = get_changelog(args.repo, args.old_version, args.new_version, structured=args.structured)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
