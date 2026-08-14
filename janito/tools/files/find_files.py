#!/usr/bin/env python3
"""
Find Files Tool - A class-based tool for finding files by name pattern and attributes.

Unlike ListFiles (which lists directory contents), FindFiles searches for files
matching criteria such as path glob patterns, file type, size, and modification
time. It is the equivalent of the Unix `find` command.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.files.find_files [args]
For AI function calling, use through the tool registry (tooling.tools_registry).

The pure filter helpers live in :mod:`janito.tools.files.find_files_utils` and
the standalone CLI harness in :mod:`janito.tools.files.find_files_cli`.
"""

import os
from typing import Any

from ...tooling import BaseTool, norm_path
from ...tooling.decorator import tool
from .find_files_utils import (
    _parse_size,
    entry_matches,
    report_result,
    report_search_start,
    time_thresholds,
)
from .gitignore_utils import (
    is_ignored_by_gitignore,
    load_gitignore_spec,
    load_janitoignore_spec,
)
from .glob_utils import matches_any_pattern


@tool(permissions="r")
class FindFiles(BaseTool):
    """
    Tool for finding files and directories by name pattern and file attributes
    such as type, size, and modification time. Unlike ListFiles, patterns are
    matched against the full relative path.

    Args:
        paths (str): Space-separated root paths to search.
        pattern (str, optional): Glob pattern matched against the full relative path
            (e.g. "*/tests/test_*.py", "docs/**/*.md", "*.py").
        exclude (str, optional): Space-separated glob patterns to exclude
            (e.g. "*/node_modules/* */__pycache__/*").
        file_type (str, optional): Filter by type: "file", "dir", or "symlink".
            Default is None (all types).
        min_size (int, optional): Minimum file size in bytes.
        max_size (int, optional): Maximum file size in bytes.
        modified_within_days (float, optional): Only include entries modified
            within the last N days.
        older_than_days (float, optional): Only include entries modified more
            than N days ago.
        max_depth (int, optional): Maximum recursion depth (None = unlimited).
        max_results (int, optional): Maximum number of results to return.
            Default is 200.
        sort_by (str, optional): Sort results by "name", "size", or "mtime".
            Default is "name".
        respect_gitignore (bool): Whether to respect .gitignore patterns.
            .janitoignore patterns are always respected. Default is True.
    """

    def run(
        self,
        paths: str,
        pattern: str | None = None,
        exclude: str | None = None,
        file_type: str | None = None,
        min_size: int | None = None,
        max_size: int | None = None,
        modified_within_days: float | None = None,
        older_than_days: float | None = None,
        max_depth: int | None = None,
        max_results: int | None = 200,
        sort_by: str | None = None,
        respect_gitignore: bool = True,
    ) -> dict[str, Any]:
        """
        Find files and directories matching the given criteria.

        Args:
            paths (str): Space-separated root paths to search.
            pattern (str, optional): Glob pattern matched against the full relative
                path (e.g. "*/tests/test_*.py", "docs/**/*.md", "*.py").
            exclude (str, optional): Space-separated glob patterns to exclude
                (e.g. "*/node_modules/* */__pycache__/*").
            file_type (str, optional): Filter by type: "file", "dir", or "symlink".
                Default is None (all types).
            min_size (int, optional): Minimum file size in bytes.
            max_size (int, optional): Maximum file size in bytes.
            modified_within_days (float, optional): Only include entries modified
                within the last N days.
            older_than_days (float, optional): Only include entries modified more
                than N days ago.
            max_depth (int, optional): Maximum recursion depth (None = unlimited).
            max_results (int, optional): Maximum number of results to return.
                Default is 200.
            sort_by (str, optional): Sort results by "name", "size", or "mtime".
                Default is "name".
            respect_gitignore (bool): Whether to respect .gitignore patterns.
                .janitoignore patterns are always respected. Default is True.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'files': list of matching relative paths
                - 'total_found': total number of matches returned
                - 'truncated': bool, True if max_results cut off results
                - 'paths': the root paths that were searched
                - 'pattern': the pattern used (if any)
                - 'stats': dict with 'entries_scanned' and 'gitignore_ignored'
                - 'error': error message if operation failed (only if success=False)
        """
        error = self._validate(file_type, sort_by, paths)
        if error:
            return error

        valid_paths, error = self._collect_valid_paths(paths)
        if error:
            return error

        exclude_patterns = exclude.strip().split() if exclude else []
        min_bytes = _parse_size(min_size)
        max_bytes = _parse_size(max_size)
        newer_than, older_than = time_thresholds(modified_within_days, older_than_days)

        report_search_start(
            self,
            valid_paths,
            pattern,
            exclude_patterns,
            file_type,
            min_bytes,
            max_bytes,
            modified_within_days,
            older_than_days,
        )

        try:
            results, stats = self._collect_results(
                valid_paths,
                pattern,
                exclude_patterns,
                file_type,
                min_bytes,
                max_bytes,
                newer_than,
                older_than,
                max_depth,
                max_results,
                respect_gitignore,
            )
        except Exception as e:
            self.report_error(f"Error during file search: {e!s}")
            return {
                "success": False,
                "error": str(e),
                "paths": paths,
                "pattern": pattern,
            }

        files, truncated = self._finalize_results(results, max_results, sort_by)
        report_result(self, files, stats, truncated)

        return {
            "success": True,
            "files": files,
            "total_found": len(files),
            "truncated": truncated,
            "paths": paths,
            "pattern": pattern,
            "stats": stats,
        }

    # ------------------------------------------------------------------

    def _validate(
        self,
        file_type: str | None,
        sort_by: str | None,
        paths: str,
    ) -> dict[str, Any] | None:
        """Validate file_type/sort_by; return an error result or None."""
        valid_types = {"file", "dir", "symlink"}
        if file_type is not None and file_type not in valid_types:
            msg = (
                f"Invalid file_type '{file_type}'. Must be one of: "
                f"{', '.join(sorted(valid_types))}"
            )
            self.report_error(msg)
            return {"success": False, "error": msg, "paths": paths}
        valid_sorts = {"name", "size", "mtime"}
        if sort_by is not None and sort_by not in valid_sorts:
            msg = (
                f"Invalid sort_by '{sort_by}'. Must be one of: "
                f"{', '.join(sorted(valid_sorts))}"
            )
            self.report_error(msg)
            return {"success": False, "error": msg, "paths": paths}
        return None

    def _collect_valid_paths(
        self, paths: str
    ) -> tuple[list[str], dict[str, Any] | None]:
        """Resolve the root paths; return (valid_paths, error_result)."""
        path_list = paths.strip().split()
        if not path_list:
            self.report_error("No paths provided")
            return (
                [],
                {"success": False, "error": "No paths provided", "paths": paths},
            )
        valid_paths: list[str] = []
        for p in path_list:
            abs_p = os.path.abspath(p)
            if not os.path.exists(abs_p):
                self.report_warning(f"Path does not exist: {norm_path(abs_p)}")
                continue
            valid_paths.append(abs_p)
        if not valid_paths:
            self.report_error("No valid paths to search")
            return (
                [],
                {
                    "success": False,
                    "error": "No valid paths to search",
                    "paths": paths,
                },
            )
        return valid_paths, None

    def _collect_results(
        self,
        valid_paths: list[str],
        pattern: str | None,
        exclude_patterns: list[str],
        file_type: str | None,
        min_bytes: int | None,
        max_bytes: int | None,
        newer_than: float | None,
        older_than: float | None,
        max_depth: int | None,
        max_results: int | None,
        respect_gitignore: bool,
    ) -> tuple[list[tuple[str, int, float]], dict[str, int]]:
        """Walk the roots; return (results, stats)."""
        results: list[tuple[str, int, float]] = []
        stats = {
            "entries_scanned": 0,
            "gitignore_ignored": 0,
            "janitoignore_ignored": 0,
        }

        cwd = os.getcwd()
        gitignore_spec = load_gitignore_spec(cwd) if respect_gitignore else None
        janitoignore_spec = load_janitoignore_spec(cwd)

        def is_ignored(rel_to_cwd: str, is_dir: bool = False) -> bool:
            """Check a path against .janitoignore then .gitignore."""
            if janitoignore_spec and is_ignored_by_gitignore(
                rel_to_cwd, janitoignore_spec, is_dir=is_dir
            ):
                stats["janitoignore_ignored"] += 1
                return True
            if gitignore_spec and is_ignored_by_gitignore(
                rel_to_cwd, gitignore_spec, is_dir=is_dir
            ):
                stats["gitignore_ignored"] += 1
                return True
            return False

        for root_path in valid_paths:
            if os.path.isfile(root_path):
                self._collect_single_file(
                    root_path,
                    pattern,
                    exclude_patterns,
                    file_type,
                    min_bytes,
                    max_bytes,
                    newer_than,
                    older_than,
                    results,
                    stats,
                )
                continue
            if self._walk_directory(
                root_path,
                pattern,
                exclude_patterns,
                file_type,
                min_bytes,
                max_bytes,
                newer_than,
                older_than,
                max_depth,
                max_results,
                cwd,
                is_ignored,
                results,
                stats,
            ):
                break
        return results, stats

    def _collect_single_file(
        self,
        root_path: str,
        pattern: str | None,
        exclude_patterns: list[str],
        file_type: str | None,
        min_bytes: int | None,
        max_bytes: int | None,
        newer_than: float | None,
        older_than: float | None,
        results: list[tuple[str, int, float]],
        stats: dict[str, int],
    ) -> None:
        """Check a single-file root directly."""
        stats["entries_scanned"] += 1
        rel = os.path.basename(root_path)
        try:
            st = os.stat(root_path)
        except OSError:
            return
        if entry_matches(
            rel,
            root_path,
            st,
            pattern,
            exclude_patterns,
            file_type,
            min_bytes,
            max_bytes,
            newer_than,
            older_than,
        ):
            results.append((rel, st.st_size, st.st_mtime))

    def _walk_directory(
        self,
        root_path: str,
        pattern: str | None,
        exclude_patterns: list[str],
        file_type: str | None,
        min_bytes: int | None,
        max_bytes: int | None,
        newer_than: float | None,
        older_than: float | None,
        max_depth: int | None,
        max_results: int | None,
        cwd: str,
        is_ignored,
        results: list[tuple[str, int, float]],
        stats: dict[str, int],
    ) -> bool:
        """Walk a directory root; return True when max_results was reached."""
        for dirpath, dirnames, filenames in os.walk(root_path):
            if max_depth is not None:
                depth = dirpath[len(root_path) :].count(os.sep)
                if depth > max_depth:
                    dirnames.clear()
                    continue
            dirnames[:] = self._prune_dirs(
                dirpath, dirnames, cwd, root_path, exclude_patterns, is_ignored
            )
            self._collect_dirs(
                dirpath,
                dirnames,
                root_path,
                pattern,
                exclude_patterns,
                file_type,
                min_bytes,
                max_bytes,
                newer_than,
                older_than,
                cwd,
                is_ignored,
                results,
                stats,
            )
            self._collect_files(
                dirpath,
                filenames,
                root_path,
                pattern,
                exclude_patterns,
                file_type,
                min_bytes,
                max_bytes,
                newer_than,
                older_than,
                cwd,
                is_ignored,
                results,
                stats,
            )
            if max_results is not None and len(results) >= max_results:
                return True
        return False

    def _prune_dirs(
        self,
        dirpath: str,
        dirnames: list[str],
        cwd: str,
        root_path: str,
        exclude_patterns: list[str],
        is_ignored,
    ) -> list[str]:
        """Return the dirnames to keep, pruning ignored/excluded directories."""
        kept: list[str] = []
        for d in dirnames:
            full = os.path.join(dirpath, d)
            rel_d = os.path.relpath(full, cwd)
            if is_ignored(rel_d, is_dir=True):
                continue
            if matches_any_pattern(os.path.relpath(full, root_path), exclude_patterns):
                continue
            kept.append(d)
        return kept

    def _collect_dirs(
        self,
        dirpath: str,
        dirnames: list[str],
        root_path: str,
        pattern: str | None,
        exclude_patterns: list[str],
        file_type: str | None,
        min_bytes: int | None,
        max_bytes: int | None,
        newer_than: float | None,
        older_than: float | None,
        cwd: str,
        is_ignored,
        results: list[tuple[str, int, float]],
        stats: dict[str, int],
    ) -> None:
        """Collect matching directory entries (when file_type allows dirs)."""
        if file_type is not None and file_type != "dir":
            return
        for dname in dirnames:
            stats["entries_scanned"] += 1
            full = os.path.join(dirpath, dname)
            rel = os.path.relpath(full, root_path)
            if is_ignored(os.path.relpath(full, cwd), is_dir=True):
                continue
            try:
                st = os.lstat(full)
            except OSError:
                continue
            if entry_matches(
                rel,
                full,
                st,
                pattern,
                exclude_patterns,
                file_type,
                min_bytes,
                max_bytes,
                newer_than,
                older_than,
            ):
                results.append((rel, st.st_size, st.st_mtime))

    def _collect_files(
        self,
        dirpath: str,
        filenames: list[str],
        root_path: str,
        pattern: str | None,
        exclude_patterns: list[str],
        file_type: str | None,
        min_bytes: int | None,
        max_bytes: int | None,
        newer_than: float | None,
        older_than: float | None,
        cwd: str,
        is_ignored,
        results: list[tuple[str, int, float]],
        stats: dict[str, int],
    ) -> None:
        """Collect matching file entries (when file_type allows files/symlinks)."""
        if file_type is not None and file_type not in ("file", "symlink"):
            return
        for fname in filenames:
            stats["entries_scanned"] += 1
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root_path)
            if is_ignored(os.path.relpath(full, cwd)):
                continue
            try:
                st = os.lstat(full)
            except OSError:
                continue
            if entry_matches(
                rel,
                full,
                st,
                pattern,
                exclude_patterns,
                file_type,
                min_bytes,
                max_bytes,
                newer_than,
                older_than,
            ):
                results.append((rel, st.st_size, st.st_mtime))

    def _finalize_results(
        self,
        results: list[tuple[str, int, float]],
        max_results: int | None,
        sort_by: str | None,
    ) -> tuple[list[str], bool]:
        """Truncate and sort the results; return (files, truncated)."""
        truncated = False
        if max_results is not None and len(results) > max_results:
            results = results[:max_results]
            truncated = True
        if sort_by == "size":
            results.sort(key=lambda r: r[1])
        elif sort_by == "mtime":
            results.sort(key=lambda r: r[2])
        else:
            results.sort(key=lambda r: r[0])
        files = [r[0] for r in results]
        return files, truncated


# ---------------------------------------------------------------------------
# CLI testing harness (implementation lives in find_files_cli so the tool
# module stays focused on the class).
# ---------------------------------------------------------------------------


def main():
    """Command line interface for testing the FindFiles tool."""
    from .find_files_cli import run_cli

    run_cli()


if __name__ == "__main__":
    main()
