"""
Shared search traversal helpers for the SearchText / SearchRegex tools.

The directory-walking logic (``_search_with_content``, ``_search_count_only``,
``_search_directory``, ``_count_directory_matches``, ``_too_deep``,
``_prune_dirs``) plus the :class:`_IgnoreCounter` and the result-printing
helpers were extracted from :mod:`janito.tools.files.search_base` (which
so the base tool class stays focused on the public contract.
"""

import os
from typing import Any

from ...tooling import norm_path
from .gitignore_utils import is_ignored_by_gitignore
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


class _SearchWalker:
    """Mixin providing the directory-walking search methods."""

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
