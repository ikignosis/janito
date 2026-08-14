"""
Directory-walking helpers for the :class:`FindFiles` tool.

The traversal/collection logic (``_collect_results``, ``_walk_directory``,
``_collect_dirs``, ``_collect_files``, ``_collect_single_file``,
``_prune_dirs``) lives in the :class:`_FindFilesWalker` mixin, extracted from
``find_files.py`` so the tool module stays focused on the public ``run``
contract, validation and result assembly.
"""

import os

from .find_files_utils import entry_matches
from .gitignore_utils import (
    is_ignored_by_gitignore,
    load_gitignore_spec,
    load_janitoignore_spec,
)
from .glob_utils import matches_any_pattern


class _FindFilesWalker:
    """Mixin providing the directory-walk and entry-collection methods."""

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
