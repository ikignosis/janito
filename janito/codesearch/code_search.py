"""
CodeSearch - Trigram-based code search with SQLite backend.

This module implements the main ``CodeSearch`` class, which provides
indexed code search using the trigram algorithm described by Russ Cox
in "Regular Expression Matching with a Trigram Index".

The index maps each 3-character substring (trigram) to the set of files
that contain it.  When searching for keywords, we extract the trigrams
from each keyword and intersect (AND) or union (OR) the corresponding
posting lists to find candidate files.
"""

import os
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Iterator, List, Optional, Set

from ..tools.files.gitignore_utils import (
    is_ignored_by_gitignore,
    load_gitignore_spec,
    load_janitoignore_spec,
)
from .index import Index
from .trigram import build_trigram_query, extract_trigrams


class MATCH(Enum):
    """Match mode for keyword search."""

    AND = auto()  # All keywords must be present
    OR = auto()  # Any keyword may be present


# File extensions that are typically source code / text and worth indexing.
# Files with these extensions are indexed; others are skipped.
DEFAULT_INDEXABLE_EXTENSIONS: Set[str] = {
    # Programming languages
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cc",
    ".hh",
    ".cs",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".kts",
    ".scala",
    ".clj",
    ".cljs",
    ".hs",
    ".ml",
    ".fs",
    ".fsx",
    ".lua",
    ".pl",
    ".pm",
    ".r",
    ".m",
    ".mm",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".ps1",
    ".sql",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".xml",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    # Documentation / text
    ".md",
    ".rst",
    ".txt",
    ".adoc",
    ".tex",
    ".org",
    # Config / build
    ".dockerfile",
    ".makefile",
    ".cmake",
    ".gradle",
    ".sbt",
    ".pom",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    # Data
    ".csv",
    ".tsv",
    ".svg",
}

# Maximum file size to index (skip very large files to keep the index fast)
DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class CodeSearch:
    """
    Trigram-based code search index backed by SQLite.

    Args:
        source_path: Root directory containing the source code to index.
        index_db_path: Path to the SQLite database file.
    """

    def __init__(self, source_path: str, index_db_path: str):
        self.source_path = Path(source_path).resolve()
        self.index_db_path = index_db_path
        self._index: Optional[Index] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_index(self) -> Index:
        if self._index is None:
            self._index = Index(self.index_db_path)
        return self._index

    def _close_index(self) -> None:
        if self._index is not None:
            self._index.close()
            self._index = None

    @staticmethod
    def _is_indexable(path: Path, max_size: int = DEFAULT_MAX_FILE_SIZE) -> bool:
        """
        Determine whether a file should be indexed.

        We skip:
        - Hidden files and directories (starting with '.')
        - Files with extensions not in DEFAULT_INDEXABLE_EXTENSIONS
        - Files larger than max_size
        - Binary files (heuristic: contains a null byte in the first 8 KB)
        """
        # Skip hidden files/dirs
        for part in path.parts:
            if part.startswith("."):
                return False

        # Check extension
        ext = path.suffix.lower()
        if ext not in DEFAULT_INDEXABLE_EXTENSIONS:
            return False

        # Check size
        try:
            size = path.stat().st_size
            if size > max_size:
                return False
        except OSError:
            return False

        # Binary heuristic: check for null bytes in first 8 KB
        try:
            with open(path, "rb") as fh:
                chunk = fh.read(8192)
                if b"\x00" in chunk:
                    return False
        except OSError:
            return False

        return True

    def _iter_source_files(self) -> Iterator[Path]:
        """
        Yield all indexable files under source_path, relative to source_path.

        Files and directories matched by the ``.gitignore`` or
        ``.janitoignore`` file in the source root are skipped (same
        semantics as the other file tools: ``.janitoignore`` is always
        respected), so the index only covers files the file tools would
        search.
        """
        gitignore_spec = load_gitignore_spec(str(self.source_path))
        janitoignore_spec = load_janitoignore_spec(str(self.source_path))

        def _is_ignored(rel_path: str, is_dir: bool = False) -> bool:
            if janitoignore_spec and is_ignored_by_gitignore(
                rel_path, janitoignore_spec, is_dir=is_dir
            ):
                return True
            if gitignore_spec and is_ignored_by_gitignore(
                rel_path, gitignore_spec, is_dir=is_dir
            ):
                return True
            return False

        for root, dirs, files in os.walk(self.source_path):
            # Skip hidden and gitignored directories in-place so os.walk
            # doesn't descend into them
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and not _is_ignored(
                    Path(root).joinpath(d).relative_to(self.source_path).as_posix(),
                    is_dir=True,
                )
            ]
            for filename in files:
                filepath = Path(root) / filename
                if _is_ignored(self._relative_path(filepath)):
                    continue
                if self._is_indexable(filepath):
                    yield filepath

    def _relative_path(self, filepath: Path) -> str:
        """Return the path relative to source_path as a POSIX string."""
        return filepath.relative_to(self.source_path).as_posix()

    def _record_last_update(self, operation: str) -> None:
        """
        Store the info of the last Create()/Update() operation in the DB.

        Persists the operation name, the completion time (ISO-8601 local
        time plus Unix epoch) and the resulting file/trigram counts as a
        JSON blob in the index's ``meta`` table.

        Args:
            operation: Either ``"create"`` or ``"update"``.
        """
        index = self._get_index()
        now_local = datetime.now().astimezone()
        index.set_last_update(
            {
                "operation": operation,
                "timestamp": now_local.isoformat(),
                "timestamp_epoch": now_local.timestamp(),
                "file_count": index.file_count(),
                "trigram_count": index.trigram_count(),
            }
        )

    def _index_file(self, filepath: Path, index: Index) -> None:
        """
        Index a single file: extract trigrams and store in the index.

        If the file was previously indexed, its old trigram associations
        are removed before the new ones are added.

        Args:
            filepath: Absolute path to the file.
            index: The Index instance.
        """
        rel_path = self._relative_path(filepath)
        try:
            stat = filepath.stat()
            mtime = stat.st_mtime
            size = stat.st_size

            with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()

            trigrams = extract_trigrams(content)

            # Remove old trigram associations if the file was already indexed
            existing = index.get_file(rel_path)
            if existing is not None:
                index.delete_file(rel_path)

            file_id = index.upsert_file(rel_path, mtime, size)
            index.add_trigrams(file_id, trigrams)
        except (OSError, UnicodeDecodeError):
            # Skip files that cannot be read
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def Create(self) -> None:
        """
        Create the index database and build the index from scratch.

        This drops any existing index and re-indexes all files under
        ``source_path``.
        """
        index = self._get_index()
        index.drop_schema()
        index.create_schema()

        for filepath in self._iter_source_files():
            self._index_file(filepath, index)

        self._record_last_update("create")

    def Update(self) -> None:
        """
        Update the index for added, deleted, or changed files.

        - **Added**: files present on disk but not in the index are indexed.
        - **Deleted**: files in the index but no longer on disk are removed.
        - **Changed**: files whose last modified time differs from the
          indexed one are re-indexed.
        """
        index = self._get_index()
        index.create_schema()  # ensure schema exists

        # Build a map of currently indexed files
        indexed_files = {f["path"]: f for f in index.get_all_files()}

        # Track which indexed files we have seen on disk
        seen_paths: Set[str] = set()

        for filepath in self._iter_source_files():
            rel_path = self._relative_path(filepath)
            seen_paths.add(rel_path)

            existing = indexed_files.get(rel_path)
            if existing is None:
                # New file -> index it
                self._index_file(filepath, index)
            else:
                # Existing file -> check if it changed (by mtime)
                stat = filepath.stat()
                if stat.st_mtime != existing["mtime"]:
                    # File modified since it was indexed -> re-index
                    self._index_file(filepath, index)

        # Remove deleted files
        for indexed_path in indexed_files:
            if indexed_path not in seen_paths:
                index.delete_file(indexed_path)

        self._record_last_update("update")

    def Find(self, keywords: List[str], match: MATCH = MATCH.AND) -> Iterator[str]:
        """
        Find files containing the given keywords.

        The search uses the trigram index to identify candidate files.
        For each keyword we compute the set of trigrams that must all be
        present in a matching file.  The per-keyword trigram sets are then
        combined according to the ``match`` mode:

        - **MATCH.AND**: A file must contain ALL keywords.  We intersect
          the posting lists of all trigrams from all keywords.
        - **MATCH.OR**: A file may contain ANY keyword.  We union the
          posting lists of all trigrams from each keyword, then union
          the results across keywords.

        Keywords shorter than 3 characters cannot use the trigram index
        and are treated as matching every file (the ANY query in Russ
        Cox's terminology).  For AND searches this means the keyword is
        effectively ignored (since every file matches).  For OR searches
        it means all indexed files are returned.

        Args:
            keywords: List of keyword strings to search for.
            match: MATCH.AND (all keywords required) or MATCH.OR (any
                   keyword sufficient).

        Yields:
            Relative file paths (POSIX style) that match the query.
        """
        if not keywords:
            return

        index = self._get_index()

        # Build trigram sets for each keyword
        keyword_trigrams = build_trigram_query(keywords)

        # Separate keywords into those with trigrams and those without
        keywords_with_trigrams = {
            kw: tgs for kw, tgs in keyword_trigrams.items() if tgs
        }
        keywords_without_trigrams = {
            kw for kw, tgs in keyword_trigrams.items() if not tgs
        }

        if match == MATCH.OR and keywords_without_trigrams:
            # A short keyword in OR mode matches every file
            all_files = index.get_all_files()
            for f in all_files:
                yield f["path"]
            return

        if match == MATCH.AND and not keywords_with_trigrams:
            # All keywords are short -> every file matches (AND of ANYs)
            all_files = index.get_all_files()
            for f in all_files:
                yield f["path"]
            return

        # Compute candidate file IDs
        if match == MATCH.AND:
            # Intersect posting lists for all trigrams of all keywords
            all_trigrams: Set[str] = set()
            for tgs in keywords_with_trigrams.values():
                all_trigrams.update(tgs)

            if not all_trigrams:
                return

            # Start with the posting list of the first trigram
            candidate_ids: Optional[Set[int]] = None
            for trigram in all_trigrams:
                posting = set(index.get_posting_list(trigram))
                if candidate_ids is None:
                    candidate_ids = posting
                else:
                    candidate_ids &= posting
                # Early exit if no candidates left
                if not candidate_ids:
                    return

            if not candidate_ids:
                return

            file_ids = sorted(candidate_ids)

        else:  # MATCH.OR
            # Union posting lists for all trigrams of each keyword,
            # then union across keywords
            candidate_ids = set()
            for tgs in keywords_with_trigrams.values():
                keyword_ids: Optional[Set[int]] = None
                for trigram in tgs:
                    posting = set(index.get_posting_list(trigram))
                    if keyword_ids is None:
                        keyword_ids = posting
                    else:
                        keyword_ids &= posting
                if keyword_ids:
                    candidate_ids.update(keyword_ids)

            if not candidate_ids:
                return

            file_ids = sorted(candidate_ids)

        # Resolve file IDs to paths and yield
        path_map = index.get_file_paths(file_ids)
        for fid in file_ids:
            path = path_map.get(fid)
            if path is not None:
                yield path

    def close(self) -> None:
        """Close the index database connection."""
        self._close_index()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ------------------------------------------------------------------
    # Convenience / statistics
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """
        Return index statistics.

        Returns:
            A dict with keys: file_count, trigram_count, source_path,
            index_db_path.
        """
        index = self._get_index()
        return {
            "file_count": index.file_count(),
            "trigram_count": index.trigram_count(),
            "source_path": str(self.source_path),
            "index_db_path": self.index_db_path,
        }

    def last_update(self) -> Optional[dict]:
        """
        Return info about the last Create()/Update() operation.

        The info is read from the index database, so it persists across
        process runs.

        Returns:
            A dict with keys: operation (``"create"`` or ``"update"``),
            timestamp (ISO-8601 local time), timestamp_epoch (Unix
            seconds), file_count, trigram_count. Returns None if no
            create/update has been recorded yet (e.g. an index built
            before this feature existed).
        """
        return self._get_index().get_last_update()

    def last_modified(self) -> Optional[float]:
        """
        Return the time the index was last created or updated.

        The value is the Unix epoch timestamp (seconds) recorded by the
        most recent ``Create()`` or ``Update()`` call, read from the
        index database so it persists across process runs.

        Returns:
            The epoch seconds of the last create/update, or None if no
            create/update has been recorded yet (e.g. an index built
            before this feature existed).
        """
        info = self._get_index().get_last_update()
        if info is None:
            return None
        return info.get("timestamp_epoch")
