"""
SQLite-based inverted trigram index.

This module provides the storage layer for the code search index.
It uses SQLite to store:

1. A ``files`` table mapping file paths to file IDs and content hashes.
2. A ``trigrams`` table mapping each trigram to the set of file IDs
   that contain it (the posting list).

The posting lists are stored as JSON arrays of file IDs for simplicity
and portability.  For very large code bases a more compact binary
encoding (e.g. varint deltas) could be used, but JSON is sufficient
for moderate-sized projects and keeps the implementation readable.
"""

import json
import sqlite3
from typing import Dict, List, Optional, Set

# Schema version for forward compatibility
SCHEMA_VERSION = 1

# Metadata key under which the info of the last Create()/Update() operation
# is stored (as a JSON blob).
LAST_UPDATE_META_KEY = "last_update"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS files (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    path    TEXT UNIQUE NOT NULL,
    sha1    TEXT NOT NULL,
    mtime   REAL NOT NULL,
    size    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS trigrams (
    trigram TEXT NOT NULL,
    file_id INTEGER NOT NULL,
    PRIMARY KEY (trigram, file_id)
);

CREATE INDEX IF NOT EXISTS idx_trigrams_trigram ON trigrams(trigram);
CREATE INDEX IF NOT EXISTS idx_trigrams_file_id ON trigrams(file_id);
"""


class Index:
    """
    SQLite-backed inverted trigram index.

    Args:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def create_schema(self) -> None:
        """Create the database schema if it does not exist."""
        conn = self._get_conn()
        conn.executescript(_SCHEMA_SQL)
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )
        conn.commit()

    def drop_schema(self) -> None:
        """Drop all tables (for rebuilding from scratch)."""
        conn = self._get_conn()
        conn.executescript(
            """
            DROP TABLE IF EXISTS trigrams;
            DROP TABLE IF EXISTS files;
            DROP TABLE IF EXISTS meta;
        """
        )
        conn.commit()

    # ------------------------------------------------------------------
    # Metadata (meta table)
    # ------------------------------------------------------------------

    def set_meta(self, key: str, value: str) -> None:
        """
        Store a metadata key/value pair in the meta table.

        Args:
            key: Metadata key.
            value: Metadata value (stored as text).
        """
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()

    def get_meta(self, key: str) -> Optional[str]:
        """
        Retrieve a metadata value by key.

        Args:
            key: Metadata key.

        Returns:
            The stored value, or None if the key is absent (or the meta
            table does not exist yet, e.g. on a fresh database).
        """
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = ?", (key,)
            ).fetchone()
        except sqlite3.Error:
            # meta table does not exist yet -> no recorded value.
            return None
        if row is None:
            return None
        return row[0]

    def set_last_update(self, info: dict) -> None:
        """
        Store the info of the last Create()/Update() operation.

        The dict is serialized to JSON and stored under the
        ``last_update`` metadata key, so it survives closing/reopening
        the index.

        Args:
            info: Dict describing the last update (e.g. operation,
                timestamp, file_count, trigram_count).
        """
        self.set_meta(LAST_UPDATE_META_KEY, json.dumps(info))

    def get_last_update(self) -> Optional[dict]:
        """
        Retrieve the info of the last Create()/Update() operation.

        Returns:
            The stored dict, or None if no create/update has been
            recorded yet (e.g. an index built before this feature).
        """
        raw = self.get_meta(LAST_UPDATE_META_KEY)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # File metadata
    # ------------------------------------------------------------------

    def upsert_file(self, path: str, sha1: str, mtime: float, size: int) -> int:
        """
        Insert or update a file record and return its file ID.

        Args:
            path: Relative file path.
            sha1: SHA-1 hash of the file content.
            mtime: Modification time (seconds since epoch).
            size: File size in bytes.

        Returns:
            The file ID (integer primary key).
        """
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO files(path, sha1, mtime, size)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                sha1 = excluded.sha1,
                mtime = excluded.mtime,
                size  = excluded.size
            """,
            (path, sha1, mtime, size),
        )
        conn.commit()
        # Get the file ID (whether inserted or updated)
        row = conn.execute("SELECT id FROM files WHERE path = ?", (path,)).fetchone()
        return row[0]

    def get_file(self, path: str) -> Optional[dict]:
        """
        Retrieve a file record by path.

        Returns:
            A dict with keys id, path, sha1, mtime, size, or None.
        """
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, path, sha1, mtime, size FROM files WHERE path = ?",
            (path,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "path": row[1],
            "sha1": row[2],
            "mtime": row[3],
            "size": row[4],
        }

    def get_all_files(self) -> List[dict]:
        """
        Retrieve all file records.

        Returns:
            A list of dicts with keys id, path, sha1, mtime, size.
        """
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, path, sha1, mtime, size FROM files ORDER BY path"
        ).fetchall()
        return [
            {"id": r[0], "path": r[1], "sha1": r[2], "mtime": r[3], "size": r[4]}
            for r in rows
        ]

    def delete_file(self, path: str) -> None:
        """Delete a file record and all its trigram associations."""
        conn = self._get_conn()
        row = conn.execute("SELECT id FROM files WHERE path = ?", (path,)).fetchone()
        if row is not None:
            file_id = row[0]
            conn.execute("DELETE FROM trigrams WHERE file_id = ?", (file_id,))
            conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
            conn.commit()

    def delete_all_files(self) -> None:
        """Delete all file records and trigram associations."""
        conn = self._get_conn()
        conn.execute("DELETE FROM trigrams")
        conn.execute("DELETE FROM files")
        conn.commit()

    # ------------------------------------------------------------------
    # Trigram posting lists
    # ------------------------------------------------------------------

    def add_trigrams(self, file_id: int, trigrams: Set[str]) -> None:
        """
        Add trigrams for a file.

        Args:
            file_id: The file ID.
            trigrams: A set of trigram strings.
        """
        conn = self._get_conn()
        conn.executemany(
            "INSERT OR IGNORE INTO trigrams(trigram, file_id) VALUES (?, ?)",
            [(t, file_id) for t in trigrams],
        )
        conn.commit()

    def get_posting_list(self, trigram: str) -> List[int]:
        """
        Get the posting list (file IDs) for a trigram.

        Returns:
            A sorted list of file IDs.
        """
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT file_id FROM trigrams WHERE trigram = ? ORDER BY file_id",
            (trigram,),
        ).fetchall()
        return [r[0] for r in rows]

    def get_posting_lists(self, trigrams: Set[str]) -> Dict[str, List[int]]:
        """
        Get posting lists for multiple trigrams.

        Returns:
            A dict mapping each trigram to its sorted list of file IDs.
        """
        result: Dict[str, List[int]] = {}
        for t in trigrams:
            result[t] = self.get_posting_list(t)
        return result

    def get_file_paths(self, file_ids: List[int]) -> Dict[int, str]:
        """
        Resolve file IDs to paths.

        Returns:
            A dict mapping file ID to path.
        """
        if not file_ids:
            return {}
        conn = self._get_conn()
        placeholders = ",".join("?" for _ in file_ids)
        rows = conn.execute(
            f"SELECT id, path FROM files WHERE id IN ({placeholders})",
            file_ids,
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def file_count(self) -> int:
        """Return the number of indexed files."""
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) FROM files").fetchone()
        return row[0]

    def trigram_count(self) -> int:
        """Return the number of distinct trigrams."""
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(DISTINCT trigram) FROM trigrams").fetchone()
        return row[0]
