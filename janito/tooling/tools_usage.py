"""
Tool usage tracking backed by an SQLite database.

Every time a tool is invoked (from either the CLI agent loop or the web
backend), :func:`record_tool_use` should be called with the tool's name. The
usage counters are persisted in ``tools_use.db`` inside the Janito config
directory (see :mod:`janito.config_dir`), in a single table with the columns
``tool_name`` and ``use_count``.

The functions in this module are deliberately defensive: they never raise.
Tracking is a best-effort side feature and must not be able to break tool
execution or the agent loop, so every database access is wrapped and failures
are swallowed (optionally logged).
"""

from __future__ import annotations

import logging
import sqlite3
import threading

from ..config_dir import get_config_dir

logger = logging.getLogger(__name__)

# Name of the SQLite database file stored in the config directory.
DB_FILENAME = "tools_use.db"

# Serialises access from the multiple threads the web backend uses to run
# tools concurrently. SQLite itself is also thread-safe with ``check_same_thread
# = False``, but a lock keeps the read-modify-write upsert atomic and cheap.
_lock = threading.Lock()


def get_db_path():
    """Return the path to the ``tools_use.db`` file in the config directory.

    Returns:
        pathlib.Path: ``<config_dir>/tools_use.db``.
    """
    return get_config_dir() / DB_FILENAME


def _connect() -> sqlite3.Connection:
    """Open a connection to the usage database, creating the schema if needed.

    The parent config directory is created on demand so the database can be
    written even on a fresh installation.

    Returns:
        sqlite3.Connection: An open connection with the ``tools_use`` table
            guaranteed to exist.
    """
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tools_use (
            tool_name TEXT PRIMARY KEY,
            use_count INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.commit()
    return conn


def record_tool_use(tool_name: str) -> None:
    """Increment (and persist) the usage counter for ``tool_name``.

    Inserts a new row with a count of ``1`` the first time a tool is seen, and
    increments the existing count on subsequent calls. This function never
    raises; any database error is logged and ignored.

    Args:
        tool_name: The name of the tool that was invoked.
    """
    if not tool_name:
        return

    try:
        with _lock:
            conn = _connect()
            try:
                conn.execute(
                    """
                    INSERT INTO tools_use (tool_name, use_count)
                    VALUES (?, 1)
                    ON CONFLICT(tool_name) DO UPDATE SET
                        use_count = use_count + 1
                    """,
                    (tool_name,),
                )
                conn.commit()
            finally:
                conn.close()
    except Exception as e:  # noqa: BLE001 - tracking must never break execution
        logger.debug(f"Failed to record tool usage for '{tool_name}': {e}")


def get_tool_use_count(tool_name: str) -> int:
    """Return the recorded usage count for a single tool.

    Args:
        tool_name: The name of the tool to look up.

    Returns:
        int: The number of recorded uses, or ``0`` if the tool has never been
            used (or if the database cannot be read).
    """
    try:
        with _lock:
            conn = _connect()
            try:
                cursor = conn.execute(
                    "SELECT use_count FROM tools_use WHERE tool_name = ?",
                    (tool_name,),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0
            finally:
                conn.close()
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Failed to read tool usage for '{tool_name}': {e}")
        return 0


def get_all_tool_uses() -> dict[str, int]:
    """Return usage counts for every tracked tool.

    Returns:
        dict[str, int]: Mapping of tool name to usage count, ordered from the
            most-used tool to the least-used. Empty if nothing has been
            recorded or the database cannot be read.
    """
    try:
        with _lock:
            conn = _connect()
            try:
                cursor = conn.execute(
                    "SELECT tool_name, use_count FROM tools_use "
                    "ORDER BY use_count DESC, tool_name ASC"
                )
                return {name: int(count) for name, count in cursor.fetchall()}
            finally:
                conn.close()
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Failed to read tool usage: {e}")
        return {}


def main() -> None:
    """Command line interface for inspecting the tool usage database."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Inspect the Janito tool usage database."
    )
    parser.add_argument(
        "tool",
        nargs="?",
        help="Optional tool name to look up a single count.",
    )
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output in JSON format.",
    )
    args = parser.parse_args()

    if args.tool:
        count = get_tool_use_count(args.tool)
        if args.json:
            print(json.dumps({"tool_name": args.tool, "use_count": count}))
        else:
            print(f"{args.tool}: {count}")
        return

    uses = get_all_tool_uses()
    if args.json:
        print(json.dumps(uses, indent=2))
        return

    if not uses:
        print("No tool usage recorded yet.")
        return

    width = max(len(name) for name in uses)
    for name, count in uses.items():
        print(f"  {name.ljust(width)}  {count}")


if __name__ == "__main__":
    main()
