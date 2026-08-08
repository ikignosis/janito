"""
Command-line harness for the :class:`FindFiles` tool.

The ``run_cli()`` entry point implements the argparse-based standalone runner
that ``python -m janito.tools.files.find_files`` invokes through the thin
``main()`` in the tool module.
"""

import json


def run_cli() -> None:
    """Command line interface for testing the FindFiles tool."""
    import argparse

    from .find_files import FindFiles

    parser = argparse.ArgumentParser(
        description="Find files by name pattern and attributes"
    )
    parser.add_argument("paths", help="Space-separated root paths to search")
    parser.add_argument(
        "--pattern", "-p", help="Glob pattern for the full relative path"
    )
    parser.add_argument(
        "--exclude", "-e", help="Space-separated glob patterns to exclude"
    )
    parser.add_argument(
        "--type",
        "-t",
        dest="file_type",
        choices=["file", "dir", "symlink"],
        help="Filter by entry type",
    )
    parser.add_argument("--min-size", type=int, help="Minimum file size in bytes")
    parser.add_argument("--max-size", type=int, help="Maximum file size in bytes")
    parser.add_argument(
        "--modified-within-days",
        type=float,
        help="Modified within the last N days",
    )
    parser.add_argument(
        "--older-than-days",
        type=float,
        help="Modified more than N days ago",
    )
    parser.add_argument("--max-depth", "-d", type=int, help="Maximum recursion depth")
    parser.add_argument(
        "--max-results", "-m", type=int, default=200, help="Maximum results"
    )
    parser.add_argument(
        "--sort-by",
        "-s",
        choices=["name", "size", "mtime"],
        help="Sort order for results",
    )
    parser.add_argument(
        "--no-gitignore", action="store_true", help="Disable .gitignore filtering"
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )

    args = parser.parse_args()

    result = FindFiles().run(
        paths=args.paths,
        pattern=args.pattern,
        exclude=args.exclude,
        file_type=args.file_type,
        min_size=args.min_size,
        max_size=args.max_size,
        modified_within_days=args.modified_within_days,
        older_than_days=args.older_than_days,
        max_depth=args.max_depth,
        max_results=args.max_results,
        sort_by=args.sort_by,
        respect_gitignore=not args.no_gitignore,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"Found {result['total_found']} matches:")
            if result.get("truncated"):
                print("  (results truncated)")
            stats = result.get("stats", {})
            ignore_msgs = []
            if stats.get("gitignore_ignored", 0) > 0:
                ignore_msgs.append(
                    f"{stats['gitignore_ignored']} ignored by .gitignore"
                )
            if stats.get("janitoignore_ignored", 0) > 0:
                ignore_msgs.append(
                    f"{stats['janitoignore_ignored']} ignored by .janitoignore"
                )
            if ignore_msgs:
                print(f"  ({', '.join(ignore_msgs)})")
            print("-" * 40)
            for f in result["files"]:
                print(f"  {f}")
        else:
            print(f"Error: {result['error']}")
