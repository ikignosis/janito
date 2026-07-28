#!/usr/bin/env python3
"""
Find Files Tool - A class-based tool for finding files by name pattern and attributes.

Unlike ListFiles (which lists directory contents), FindFiles searches for files
matching criteria such as path glob patterns, file type, size, and modification
time. It is the equivalent of the Unix `find` command.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.files.find_files [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import fnmatch
import json
import os
import time
from typing import Any

from ...tooling import BaseTool, norm_path
from ...tooling.decorator import tool
from .gitignore_utils import is_ignored_by_gitignore, load_gitignore_spec


def _matches_any_pattern(path: str, patterns: list[str]) -> bool:
    """
    Check if a path matches any of the given glob patterns.

    Matching is performed against both the full relative path (with '/'
    separators) and the basename, so patterns like '*.py' and
    '*/tests/*.py' both work as expected.

    Args:
        path (str): The relative path to check (OS-normalised).
        patterns (list[str]): List of glob patterns.

    Returns:
        bool: True if any pattern matches.
    """
    # Normalise to forward slashes so patterns are platform-independent
    normalised = path.replace(os.sep, "/")
    basename = os.path.basename(normalised)

    for pat in patterns:
        if fnmatch.fnmatch(normalised, pat) or fnmatch.fnmatch(basename, pat):
            return True
    return False


def _parse_size(value: int | str | None) -> int | None:
    """
    Parse a human-friendly size value into bytes.

    Accepts plain integers (bytes) or strings with a suffix:
    KB, MB, GB (case-insensitive, powers of 1024).

    Args:
        value: An int (bytes) or a string like "10MB", "512kb", "1GB".

    Returns:
        int or None: Size in bytes, or None if value is None.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)

    value = value.strip().upper()
    multipliers = {
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
    }
    for suffix, mult in multipliers.items():
        if value.endswith(suffix):
            number = value[: -len(suffix)].strip()
            return int(float(number) * mult)

    return int(value)


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
            Default is True.
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
                Default is True.

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
        try:
            # ── Validate file_type ──
            valid_types = {"file", "dir", "symlink"}
            if file_type is not None and file_type not in valid_types:
                self.report_error(
                    f"Invalid file_type '{file_type}'. Must be one of: {', '.join(sorted(valid_types))}"
                )
                return {
                    "success": False,
                    "error": f"Invalid file_type '{file_type}'. Must be one of: {', '.join(sorted(valid_types))}",
                    "paths": paths,
                }

            # ── Validate sort_by ──
            valid_sorts = {"name", "size", "mtime"}
            if sort_by is not None and sort_by not in valid_sorts:
                self.report_error(
                    f"Invalid sort_by '{sort_by}'. Must be one of: {', '.join(sorted(valid_sorts))}"
                )
                return {
                    "success": False,
                    "error": f"Invalid sort_by '{sort_by}'. Must be one of: {', '.join(sorted(valid_sorts))}",
                    "paths": paths,
                }

            # ── Parse root paths ──
            path_list = paths.strip().split()
            if not path_list:
                self.report_error("No paths provided")
                return {"success": False, "error": "No paths provided", "paths": paths}

            valid_paths: list[str] = []
            for p in path_list:
                abs_p = os.path.abspath(p)
                if not os.path.exists(abs_p):
                    self.report_warning(f"Path does not exist: {norm_path(abs_p)}")
                    continue
                valid_paths.append(abs_p)

            if not valid_paths:
                self.report_error("No valid paths to search")
                return {
                    "success": False,
                    "error": "No valid paths to search",
                    "paths": paths,
                }

            # ── Parse exclude patterns ──
            exclude_patterns: list[str] = []
            if exclude:
                exclude_patterns = exclude.strip().split()

            # ── Parse size limits ──
            min_bytes = _parse_size(min_size)
            max_bytes = _parse_size(max_size)

            # ── Compute time thresholds ──
            now = time.time()
            newer_than: float | None = None
            older_than: float | None = None
            if modified_within_days is not None:
                newer_than = now - modified_within_days * 86400
            if older_than_days is not None:
                older_than = now - older_than_days * 86400

            # ── Load .gitignore from the current working directory ──
            cwd = os.getcwd()
            gitignore_spec = None
            if respect_gitignore:
                gitignore_spec = load_gitignore_spec(cwd)

            # ── Report start ──
            paths_str = ", ".join(norm_path(p) for p in valid_paths[:3])
            if len(valid_paths) > 3:
                paths_str += f" (+{len(valid_paths) - 3} more)"
            criteria: list[str] = []
            if pattern:
                criteria.append(f"pattern='{pattern}'")
            if file_type:
                criteria.append(f"type={file_type}")
            if min_bytes is not None or max_bytes is not None:
                size_desc = []
                if min_bytes is not None:
                    size_desc.append(f">={min_bytes}B")
                if max_bytes is not None:
                    size_desc.append(f"<={max_bytes}B")
                criteria.append(f"size {','.join(size_desc)}")
            if modified_within_days is not None:
                criteria.append(f"modified <{modified_within_days}d")
            if older_than_days is not None:
                criteria.append(f"older >{older_than_days}d")

            criteria_str = f" [{', '.join(criteria)}]" if criteria else ""
            self.report_start(f"🔎 Finding files in {paths_str}{criteria_str}", end="")

            # ── Walk and collect ──
            results: list[tuple[str, int, float]] = []  # (rel_path, size, mtime)
            entries_scanned = 0
            gitignore_ignored = 0
            truncated = False

            for root_path in valid_paths:
                if os.path.isfile(root_path):
                    # Single-file root — just check it directly
                    entries_scanned += 1
                    rel = os.path.basename(root_path)
                    try:
                        st = os.stat(root_path)
                    except OSError:
                        continue
                    if self._entry_matches(
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
                        None,
                    ):
                        results.append((rel, st.st_size, st.st_mtime))
                    continue

                # Directory root — walk
                for dirpath, dirnames, filenames in os.walk(root_path):
                    # Depth check
                    if max_depth is not None:
                        depth = dirpath[len(root_path) :].count(os.sep)
                        if depth > max_depth:
                            dirnames.clear()
                            continue

                    # Prune gitignored directories (match relative to cwd)
                    if gitignore_spec:
                        kept: list[str] = []
                        for d in dirnames:
                            rel_d = os.path.relpath(os.path.join(dirpath, d), cwd)
                            if is_ignored_by_gitignore(
                                rel_d, gitignore_spec, is_dir=True
                            ):
                                gitignore_ignored += 1
                            else:
                                kept.append(d)
                        dirnames[:] = kept

                    # Process directories (when file_type is None or "dir")
                    if file_type is None or file_type == "dir":
                        for dname in dirnames:
                            entries_scanned += 1
                            full = os.path.join(dirpath, dname)
                            rel = os.path.relpath(full, root_path)

                            if gitignore_spec and is_ignored_by_gitignore(
                                os.path.relpath(full, cwd),
                                gitignore_spec,
                                is_dir=True,
                            ):
                                gitignore_ignored += 1
                                continue

                            try:
                                st = os.lstat(full)
                            except OSError:
                                continue

                            if self._entry_matches(
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
                                gitignore_spec,
                            ):
                                results.append((rel, st.st_size, st.st_mtime))

                    # Process files
                    if file_type is None or file_type in ("file", "symlink"):
                        for fname in filenames:
                            entries_scanned += 1
                            full = os.path.join(dirpath, fname)
                            rel = os.path.relpath(full, root_path)

                            if gitignore_spec and is_ignored_by_gitignore(
                                os.path.relpath(full, cwd), gitignore_spec
                            ):
                                gitignore_ignored += 1
                                continue

                            try:
                                st = os.lstat(full)
                            except OSError:
                                continue

                            if self._entry_matches(
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
                                gitignore_spec,
                            ):
                                results.append((rel, st.st_size, st.st_mtime))

                    # Early exit if we already have enough
                    if max_results is not None and len(results) >= max_results:
                        break

                if max_results is not None and len(results) >= max_results:
                    break

            # ── Truncate ──
            if max_results is not None and len(results) > max_results:
                results = results[:max_results]
                truncated = True

            # ── Sort ──
            if sort_by == "size":
                results.sort(key=lambda r: r[1])
            elif sort_by == "mtime":
                results.sort(key=lambda r: r[2])
            else:
                results.sort(key=lambda r: r[0])

            files = [r[0] for r in results]

            # ── Report result ──
            extra = " (truncated)" if truncated else ""
            gi_msg = (
                f", {gitignore_ignored} ignored by .gitignore"
                if gitignore_ignored
                else ""
            )
            self.report_result(
                f"Found {len(files)} matches from {entries_scanned} entries{extra}{gi_msg}"
            )

            return {
                "success": True,
                "files": files,
                "total_found": len(files),
                "truncated": truncated,
                "paths": paths,
                "pattern": pattern,
                "stats": {
                    "entries_scanned": entries_scanned,
                    "gitignore_ignored": gitignore_ignored,
                },
            }

        except Exception as e:
            self.report_error(f"Error during file search: {e!s}")
            return {
                "success": False,
                "error": str(e),
                "paths": paths,
                "pattern": pattern,
            }

    # ── private helpers ──────────────────────────────────────────────

    @staticmethod
    def _entry_matches(
        rel_path: str,
        full_path: str,
        st: os.stat_result,
        pattern: str | None,
        exclude_patterns: list[str],
        file_type: str | None,
        min_bytes: int | None,
        max_bytes: int | None,
        newer_than: float | None,
        older_than: float | None,
        gitignore_spec,
    ) -> bool:
        """Return True if a single filesystem entry passes all filters."""
        import stat as stat_mod

        # ── type check ──
        if file_type is not None:
            is_link = stat_mod.S_ISLNK(st.st_mode)
            if file_type == "symlink":
                if not is_link:
                    return False
            elif file_type == "dir":
                if not stat_mod.S_ISDIR(st.st_mode):
                    return False
            elif file_type == "file":
                # A symlink to a file is NOT a regular file
                if is_link or not stat_mod.S_ISREG(st.st_mode):
                    return False

        # ── pattern check (full relative path) ──
        if pattern is not None:
            if not _matches_any_pattern(rel_path, [pattern]):
                return False

        # ── exclude check ──
        if exclude_patterns and _matches_any_pattern(rel_path, exclude_patterns):
            return False

        # ── size check (only meaningful for regular files) ──
        if min_bytes is not None and st.st_size < min_bytes:
            return False
        if max_bytes is not None and st.st_size > max_bytes:
            return False

        # ── mtime check ──
        if newer_than is not None and st.st_mtime < newer_than:
            return False
        if older_than is not None and st.st_mtime > older_than:
            return False

        return True


# ── CLI testing harness ────────────────────────────────────────────────────────
def main():
    """Command line interface for testing the FindFiles tool."""
    import argparse

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
            if stats.get("gitignore_ignored", 0) > 0:
                print(f"  ({stats['gitignore_ignored']} ignored by .gitignore)")
            print("-" * 40)
            for f in result["files"]:
                print(f"  {f}")
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
