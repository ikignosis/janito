#!/usr/bin/env python3
"""
Code Search Tool - Searches a pre-built trigram code search index.

This tool queries the SQLite trigram index at ``./.janito/codesearch.db``
(built with ``janito --init-codesearch``) using the ``janito.codesearch``
package. It is only loaded when that index database exists in the current
working directory (see ``should_load``).

For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import json
import time
from pathlib import Path
from typing import Any

from ...codesearch import MATCH
from ...codesearch import CodeSearch as CodeSearchEngine
from ...tooling import BaseTool, norm_path
from ...tooling.decorator import tool
from ...tooling.reporter import report_progress

# Per-project location of the code search index (same as the one created by
# the ``--init-codesearch`` CLI flag).
INDEX_DB_RELPATH = Path(".janito") / "codesearch.db"

# Time-to-live for the index: when the last recorded update is older than
# this, the index is refreshed in place (an incremental Update()) during
# tool load (should_load) before being offered to the model.
INDEX_TTL_SECONDS = 24 * 60 * 60  # 1 day


@tool(permissions="r")
class CodeSearch(BaseTool):
    """
    Tool for searching a pre-built trigram code search index.

    Searches the SQLite trigram index at ./.janito/codesearch.db (created
    with `janito --init-codesearch`) for lines whose contents contain the
    given keywords. Keywords are matched as whole words (so `foo` does not
    match `foobar` or `foo_bar`), and the results include the file path,
    line number and line content, in the same "path:lineno: content" format
    used by the other search tools. With match="and" a line must contain
    all keywords; with match="or" any keyword is sufficient.

    Args:
        keywords (list[str]): List of keywords to search for, matched as
            whole words. Files are narrowed through the trigram index;
            keywords shorter than 3 characters cannot be indexed and are
            matched by scanning candidate files directly.
        match (str): Match mode - "and" (all keywords must be present on
            a line) or "or" (any keyword is sufficient). Defaults to "and".
    """

    @classmethod
    def should_load(cls) -> bool:
        """
        Only load this tool when a code search index exists in the working dir.

        If the index exists but its last recorded update is missing (e.g.
        an index built before last-update tracking) or older than
        ``INDEX_TTL_SECONDS`` (1 day), the index is refreshed in place
        with an incremental ``Update()`` before the tool is offered to the
        model. A refresh failure never prevents loading: the tool remains
        usable with the existing (possibly stale) index.

        Returns:
            bool: True if ./.janito/codesearch.db exists, False otherwise
        """
        index_db_path = Path.cwd() / INDEX_DB_RELPATH
        if not index_db_path.is_file():
            cls._load_skip_reason = (
                "no code search index at ./.janito/codesearch.db (build it with "
                "`janito --init-codesearch`)"
            )
            return False
        try:
            cls._refresh_if_stale(index_db_path)
        except Exception:
            # Never let a refresh failure break discovery: the tool is still
            # usable with the existing (possibly stale) index.
            pass
        return True

    @classmethod
    def _refresh_if_stale(cls, index_db_path: Path) -> None:
        """
        Refresh the index in place when it is missing or older than the TTL.

        Compares the index's last recorded modification time against
        ``INDEX_TTL_SECONDS``; when it is absent or older, runs an
        incremental ``Update()`` over the working directory.

        Args:
            index_db_path: Path to the index database.
        """
        with CodeSearchEngine(str(Path.cwd()), str(index_db_path)) as cs:
            last_modified = cs.last_modified()
            if (
                last_modified is None
                or (time.time() - last_modified) > INDEX_TTL_SECONDS
            ):
                report_progress(
                    "Code search index is stale (last update missing or older than 1 day), refreshing in place..."
                )
                cs.Update()

    def run(
        self,
        keywords: list[str],
        match: str = "and",
    ) -> dict[str, Any]:
        """
        Search the code search index for lines containing the given keywords.

        Args:
            keywords (list[str]): List of keywords to search for, matched as
                whole words. Files are narrowed through the trigram index;
                keywords shorter than 3 characters cannot be indexed and are
                matched by scanning candidate files directly.
            match (str): Match mode - "and" (all keywords must be present on
                a line) or "or" (any keyword is sufficient). Defaults to "and".

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if the search succeeded
                - 'keywords': the keywords that were searched for
                - 'match': the match mode used ("and" or "or")
                - 'matches': list of matching lines formatted as
                  'path:lineno: line_content' (the same format used by the
                  SearchText / SearchRegex tools)
                - 'total_matches': number of matching lines
                - 'error': error message if the search failed (only present
                  if success=False)
        """
        try:
            match_mode_str = match.strip().lower()
            if match_mode_str == "and":
                match_mode = MATCH.AND
            elif match_mode_str == "or":
                match_mode = MATCH.OR
            else:
                self.report_error(
                    f"Invalid match mode '{match}' (expected 'and' or 'or')"
                )
                return {
                    "success": False,
                    "error": f"Invalid match mode '{match}' (expected 'and' or 'or')",
                    "keywords": keywords,
                    "match": match,
                }

            index_db_path = Path.cwd() / INDEX_DB_RELPATH
            if not index_db_path.is_file():
                self.report_error(
                    f"Code search index not found at {norm_path(str(index_db_path))}"
                )
                return {
                    "success": False,
                    "error": (
                        f"Code search index not found at {index_db_path}. Build it with `janito --init-codesearch`."
                    ),
                    "keywords": keywords,
                    "match": match_mode_str,
                }

            self.report_start(
                f"\U0001f50d Searching code index for "
                f"{', '.join(keywords) or '(no keywords)'} ({match_mode_str} match)",
                end="",
            )

            matches: list[str] = []
            with CodeSearchEngine(str(Path.cwd()), str(index_db_path)) as cs:
                for m in cs.Find(keywords, match_mode):
                    matches.append(m.format())

            self.report_result(f"Found {len(matches)} matching lines")

            return {
                "success": True,
                "keywords": keywords,
                "match": match_mode_str,
                "matches": matches,
                "total_matches": len(matches),
            }

        except Exception as e:
            self.report_error(f"Error during code search: {e!s}")
            return {
                "success": False,
                "error": str(e),
                "keywords": keywords,
                "match": match,
            }


# CLI interface for testing
def main():
    """Command line interface for testing the CodeSearch tool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Search the code search index for AI function calling"
    )
    parser.add_argument("keywords", nargs="+", help="Keywords to search for")
    parser.add_argument(
        "--match",
        choices=["and", "or"],
        default="and",
        help="Match mode: 'and' (all keywords) or 'or' (any keyword) (default: and)",
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )
    args = parser.parse_args()

    result = CodeSearch().run(keywords=args.keywords, match=args.match)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(
                f"Found {result['total_matches']} matching lines ({result['match']} match):"
            )
            for match in result["matches"]:
                print(f"  {match}")
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
