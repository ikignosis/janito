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
from .gitignore_utils import (
    is_ignored_by_gitignore,
    load_gitignore_spec,
    load_janitoignore_spec,
)
from .glob_utils import matches_any_pattern


class _IgnoreCounter:
    """Count entries skipped due to the .janitoignore / .gitignore specs.

    Args:
        cwd: The directory the specs were loaded from; paths are matched
            relative to it. When None (no specs in scope) nothing is ignored.
        gitignore_spec: The parsed .gitignore spec, or None when disabled.
        janitoignore_spec: The parsed .janitoignore spec, or None.
    """

    def __init__(self, cwd, gitignore_spec, janitoignore_spec):
        self.cwd = cwd
        self.gitignore_spec = gitignore_spec
        self.janitoignore_spec = janitoignore_spec
        self.files_ignored = 0
        self.janitoignore_ignored = 0

    def is_ignored(self, abs_path: str, is_dir: bool = False) -> bool:
        """Check ``abs_path`` (relative to cwd) against .janitoignore then .gitignore."""
        if not self.cwd:
            return False
        rel_to_cwd = os.path.relpath(abs_path, self.cwd)
        if self.janitoignore_spec and is_ignored_by_gitignore(
            rel_to_cwd, self.janitoignore_spec, is_dir=is_dir
        ):
            self.janitoignore_ignored += 1
            return True
        if self.gitignore_spec and is_ignored_by_gitignore(
            rel_to_cwd, self.gitignore_spec, is_dir=is_dir
        ):
            self.files_ignored += 1
            return True
        return False


def print_search_result(result: dict[str, Any], count_only: bool) -> None:
    """Print a human-friendly summary of a search result dict."""
    if not result["success"]:
        print(f"Error: {result['error']}")
        return

    if count_only:
        print(f"Total matches: {result['total_matches']}")
        print(f"Files searched: {result['files_searched']}")
        _print_ignore_stats(result)
        if result["counts"]:
            print("\nPer-file counts:")
            for filepath, count in result["counts"].items():
                print(f"  {norm_path(filepath)}: {count}")
    else:
        print(
            f"Found {len(result['matches'])} matches in "
            f"{result['files_searched']} files:"
        )
        _print_ignore_stats(result)
        for match in result["matches"]:
            print(f"  {match}")


def _print_ignore_stats(result: dict[str, Any]) -> None:
    """Print .gitignore/.janitoignore application stats from a result dict."""
    if result.get("gitignore_applied"):
        print("Respecting .gitignore")
    if result.get("janitoignore_applied"):
        print("Respecting .janitoignore")
    ignored = result.get("files_ignored_by_gitignore", 0)
    if ignored > 0:
        print(f"Files ignored by .gitignore: {ignored}")
    janito_ignored = result.get("files_ignored_by_janitoignore", 0)
    if janito_ignored > 0:
        print(f"Files ignored by .janitoignore: {janito_ignored}")


class SearchRunner(BaseTool):
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

    def _search_with_content(
        self,
        paths: list[str],
        term: str,
        case_sensitive: bool,
        max_depth: int | None,
        max_results: int | None,
        gitignore_spec=None,
        janitoignore_spec=None,
        cwd: str | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> dict[str, Any]:
        """Search and return matching lines with content."""
        matches = []
        files_searched = 0
        exclude_patterns = exclude_patterns or []
        tracker = _IgnoreCounter(cwd, gitignore_spec, janitoignore_spec)

        for path in paths:
            if os.path.isfile(path):
                # Skip single files matched by exclude patterns (matched
                # against the basename, like FindFiles does for file roots)
                if matches_any_pattern(os.path.basename(path), exclude_patterns):
                    continue
                # Search single file
                file_matches = self._search_file(
                    path, term, case_sensitive, max_results
                )
                if file_matches:
                    matches.extend(file_matches)
                    if max_results and len(matches) >= max_results:
                        matches = matches[:max_results]
                        break
                files_searched += 1
            else:
                # Search directory recursively
                (
                    dir_matches,
                    dir_files_searched,
                    dir_files_ignored,
                    dir_janitoignore_ignored,
                ) = self._search_directory(
                    path,
                    term,
                    case_sensitive,
                    max_depth,
                    max_results,
                    gitignore_spec,
                    janitoignore_spec,
                    cwd,
                    exclude_patterns,
                )
                matches.extend(dir_matches)
                files_searched += dir_files_searched
                tracker.files_ignored += dir_files_ignored
                tracker.janitoignore_ignored += dir_janitoignore_ignored
                if max_results and len(matches) >= max_results:
                    matches = matches[:max_results]
                    break

        return {
            "success": True,
            "matches": matches,
            "total_matches": len(matches),
            "files_searched": files_searched,
            "respect_gitignore": gitignore_spec is not None,
            "gitignore_applied": gitignore_spec is not None,
            "janitoignore_applied": janitoignore_spec is not None,
            "files_ignored_by_gitignore": tracker.files_ignored,
            "files_ignored_by_janitoignore": tracker.janitoignore_ignored,
        }

    def _search_count_only(
        self,
        paths: list[str],
        term: str,
        case_sensitive: bool,
        max_depth: int | None,
        max_results: int | None,
        gitignore_spec=None,
        janitoignore_spec=None,
        cwd: str | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> dict[str, Any]:
        """Search and return only match counts."""
        counts = {}
        total_matches = 0
        files_searched = 0
        exclude_patterns = exclude_patterns or []
        tracker = _IgnoreCounter(cwd, gitignore_spec, janitoignore_spec)

        for path in paths:
            if os.path.isfile(path):
                # Skip single files matched by exclude patterns
                if matches_any_pattern(os.path.basename(path), exclude_patterns):
                    continue
                # Count matches in single file
                file_count = self._count_file_matches(path, term, case_sensitive)
                if file_count > 0:
                    counts[norm_path(path)] = file_count
                    total_matches += file_count
                files_searched += 1
            else:
                # Count matches in directory
                (
                    dir_counts,
                    dir_total,
                    dir_files,
                    dir_ignored,
                    dir_janitoignore_ignored,
                ) = self._count_directory_matches(
                    path,
                    term,
                    case_sensitive,
                    max_depth,
                    gitignore_spec,
                    janitoignore_spec,
                    cwd,
                    exclude_patterns,
                )
                counts.update(dir_counts)
                total_matches += dir_total
                files_searched += dir_files
                tracker.files_ignored += dir_ignored
                tracker.janitoignore_ignored += dir_janitoignore_ignored

        return {
            "success": True,
            "counts": counts,
            "total_matches": total_matches,
            "files_searched": files_searched,
            "respect_gitignore": gitignore_spec is not None,
            "gitignore_applied": gitignore_spec is not None,
            "janitoignore_applied": janitoignore_spec is not None,
            "files_ignored_by_gitignore": tracker.files_ignored,
            "files_ignored_by_janitoignore": tracker.janitoignore_ignored,
        }

    @staticmethod
    def _too_deep(root: str, dirpath: str, max_depth: int | None) -> bool:
        """Return True when ``root`` is at or beyond the depth limit."""
        if max_depth is None:
            return False
        return root[len(dirpath) :].count(os.sep) >= max_depth

    @staticmethod
    def _prune_dirs(dirs, root, dirpath, tracker, exclude_patterns) -> None:
        """Filter out ignored/excluded dirs in-place (prevents walking into them)."""
        dirs[:] = [
            d
            for d in dirs
            if not tracker.is_ignored(os.path.join(root, d), is_dir=True)
            and not matches_any_pattern(
                os.path.relpath(os.path.join(root, d), dirpath),
                exclude_patterns,
            )
        ]

    def _search_directory(
        self,
        dirpath: str,
        term: str,
        case_sensitive: bool,
        max_depth: int | None,
        max_results: int | None,
        gitignore_spec=None,
        janitoignore_spec=None,
        cwd: str | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> tuple:
        """Search a directory recursively and return matches."""
        matches = []
        files_searched = 0
        exclude_patterns = exclude_patterns or []
        tracker = _IgnoreCounter(cwd, gitignore_spec, janitoignore_spec)

        try:
            for root, dirs, files in os.walk(dirpath):
                # Check depth limit
                if self._too_deep(root, dirpath, max_depth):
                    dirs.clear()  # Don't recurse deeper
                    continue

                # Filter out ignored/excluded directories
                self._prune_dirs(dirs, root, dirpath, tracker, exclude_patterns)

                for filename in files:
                    filepath = os.path.join(root, filename)

                    # Skip if ignored by .janitoignore / .gitignore (match relative to cwd)
                    if tracker.is_ignored(filepath):
                        continue

                    # Skip if excluded by glob patterns (match relative to search root)
                    if matches_any_pattern(
                        os.path.relpath(filepath, dirpath), exclude_patterns
                    ):
                        continue

                    file_matches = self._search_file(
                        filepath,
                        term,
                        case_sensitive,
                        max_results - len(matches) if max_results else None,
                    )
                    if file_matches:
                        matches.extend(file_matches)
                        if max_results and len(matches) >= max_results:
                            files_searched += 1
                            return (
                                matches[:max_results],
                                files_searched,
                                tracker.files_ignored,
                                tracker.janitoignore_ignored,
                            )

                    files_searched += 1

        except Exception:
            pass  # Skip directories that can't be accessed

        return (
            matches,
            files_searched,
            tracker.files_ignored,
            tracker.janitoignore_ignored,
        )

    def _count_directory_matches(
        self,
        dirpath: str,
        term: str,
        case_sensitive: bool,
        max_depth: int | None,
        gitignore_spec=None,
        janitoignore_spec=None,
        cwd: str | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> tuple:
        """Count matches in a directory recursively."""
        counts = {}
        total_matches = 0
        files_searched = 0
        exclude_patterns = exclude_patterns or []
        tracker = _IgnoreCounter(cwd, gitignore_spec, janitoignore_spec)

        try:
            for root, dirs, files in os.walk(dirpath):
                # Check depth limit
                if self._too_deep(root, dirpath, max_depth):
                    dirs.clear()  # Don't recurse deeper
                    continue

                # Filter out ignored/excluded directories
                self._prune_dirs(dirs, root, dirpath, tracker, exclude_patterns)

                for filename in files:
                    filepath = os.path.join(root, filename)

                    # Skip if ignored by .janitoignore / .gitignore (match relative to cwd)
                    if tracker.is_ignored(filepath):
                        continue

                    # Skip if excluded by glob patterns (match relative to search root)
                    if matches_any_pattern(
                        os.path.relpath(filepath, dirpath), exclude_patterns
                    ):
                        continue

                    file_count = self._count_file_matches(
                        filepath, term, case_sensitive
                    )
                    if file_count > 0:
                        counts[norm_path(filepath)] = file_count
                        total_matches += file_count
                    files_searched += 1

        except Exception:
            pass  # Skip directories that can't be accessed

        return (
            counts,
            total_matches,
            files_searched,
            tracker.files_ignored,
            tracker.janitoignore_ignored,
        )
