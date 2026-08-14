"""
Shared search machinery for the SearchText and SearchRegex tools.

Both tools walk directories the same way: respecting ``.gitignore`` (when
enabled) and ``.janitoignore``, pruning excluded glob patterns, limiting
depth and results, and aggregating per-file matches/counts. The only
difference is how a single line is matched — a plain substring for
``SearchText``, a compiled regular expression for ``SearchRegex``. This
module holds the common walking/aggregation logic so the two tools stay
thin and consistent.
"""

import os
from typing import Any

from ...tooling import BaseTool, norm_path
from .gitignore_utils import load_gitignore_spec, load_janitoignore_spec
from .search_walk import _SearchWalker


class SearchRunner(_SearchWalker, BaseTool):
    """
    Base class implementing the shared directory-walking search logic.

    Subclasses must implement ``run``, ``_search_file`` and
    ``_count_file_matches`` and configure the per-tool labels ``term_key``,
    ``error_label`` and the ``start_message`` method.
    """

    #: Key under which the searched term is echoed back in error results.
    term_key: str = "term"
    #: Label used in error messages (e.g. "regex search").
    error_label: str = "search"

    def start_message(
        self, term: str, paths_str: str, exclude_str: str | None = None
    ) -> str:
        """Return the report_start message for this tool."""
        raise NotImplementedError

    def _validate_paths(self, path_list: list[str]) -> list[str]:
        """Return the subset of paths that exist on disk."""
        valid_paths = []
        for path in path_list:
            abs_path = os.path.abspath(path)
            if not os.path.exists(abs_path):
                self.report_warning(f"Path does not exist: {norm_path(abs_path)}")
                continue
            valid_paths.append(abs_path)
        return valid_paths

    def run_search(
        self,
        paths: str,
        term: str,
        case_sensitive: bool = True,
        max_depth: int | None = None,
        max_results: int | None = 100,
        count_only: bool = False,
        respect_gitignore: bool = True,
        exclude: str | None = None,
    ) -> dict[str, Any]:
        """Run the search; mirrors the tool run() contract."""
        try:
            # Parse paths
            path_list = paths.strip().split()
            if not path_list:
                self.report_error("No paths provided")
                return {
                    "success": False,
                    "error": "No paths provided",
                    "paths": paths,
                    "respect_gitignore": respect_gitignore,
                    "exclude": exclude,
                }

            # Validate paths exist
            valid_paths = self._validate_paths(path_list)
            if not valid_paths:
                self.report_error("No valid paths to search")
                return {
                    "success": False,
                    "error": "No valid paths to search",
                    "paths": paths,
                    "respect_gitignore": respect_gitignore,
                    "exclude": exclude,
                }

            # Parse exclude patterns
            exclude_patterns = exclude.strip().split() if exclude else []

            # Load ignore specs from the current working directory.
            # .janitoignore is always respected; .gitignore only when enabled.
            cwd = os.getcwd()
            gitignore_spec = load_gitignore_spec(cwd) if respect_gitignore else None
            janitoignore_spec = load_janitoignore_spec(cwd)

            # Report start
            paths_str = ", ".join([norm_path(p) for p in valid_paths[:3]])
            if len(valid_paths) > 3:
                paths_str += f" (+{len(valid_paths) - 3} more)"
            exclude_str = " ".join(exclude_patterns) if exclude_patterns else None
            self.report_start(self.start_message(term, paths_str, exclude_str), end="")

            # Perform search
            if count_only:
                result = self._search_count_only(
                    valid_paths,
                    term,
                    case_sensitive,
                    max_depth,
                    max_results,
                    gitignore_spec,
                    janitoignore_spec,
                    cwd,
                    exclude_patterns,
                )
            else:
                result = self._search_with_content(
                    valid_paths,
                    term,
                    case_sensitive,
                    max_depth,
                    max_results,
                    gitignore_spec,
                    janitoignore_spec,
                    cwd,
                    exclude_patterns,
                )

            if result["success"]:
                if count_only:
                    self.report_result(
                        f"Found {result['total_matches']} matches in "
                        f"{result['files_searched']} files"
                    )
                else:
                    match_count = len(result["matches"])
                    self.report_result(
                        f"Found {match_count} matches in "
                        f"{result['files_searched']} files"
                    )

            return result

        except Exception as e:
            self.report_error(f"Error during {self.error_label}: {e!s}")
            return {
                "success": False,
                "error": str(e),
                "paths": paths,
                self.term_key: term,
                "respect_gitignore": respect_gitignore,
                "exclude": exclude,
            }
