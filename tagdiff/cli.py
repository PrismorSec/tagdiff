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
    parser.add_argument("--model", help="AI model to use (e.g. gpt-4o)")
    parser.add_argument("--output", help="Save result to a JSON file")
    parser.add_argument("--verbose", action="store_true", help="Show progress during execution")
    args = parser.parse_args()

    try:
        result = get_changelog(
            args.repo, 
            args.old_version, 
            args.new_version, 
            structured=args.structured,
            model=args.model,
            verbose=args.verbose
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


if __name__ == "__main__":
    sys.exit(main())
