"""Filesystem persistence for web chat sessions (issue #36).

Each conversation is stored as a JSON-lines file under
``./.janito/sessions/<session_id>.jsonl`` (relative to the current working
directory, mirroring ``./.janito/changes.jsonl`` from
:mod:`janito.tooling.changes`).

File format (one JSON object per line):

    line 1:   session metadata
              ``{"session_id", "title", "created_at", "last_active", "system_prompt"}``
    line 2+:  the OpenAI-format conversation messages (``{"role": ...}``),
              one per line, in order.

The whole file is rewritten whenever the in-memory conversation changes, so
the on-disk state always matches the session exactly — including rollbacks
(Ctrl+C / errors) and restarts (F2), which truncate the history.

Like the other best-effort tracking modules (:mod:`janito.tooling.changes`,
:mod:`janito.tooling.tools_usage`), persistence never raises: an I/O error is
logged and the in-memory session is left untouched, so an unwritable
directory or a broken disk cannot take the web server down.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Directory (relative to the current working directory) where the session
# files live. ``./.janito`` is the per-project workspace directory (it also
# holds the shell ``history.log`` and the ``changes.jsonl`` log).
SESSIONS_DIR = Path(".janito") / "sessions"

# Serialises access from the multiple threads the web backend uses.
_lock = threading.Lock()


def get_sessions_dir() -> Path:
    """Return the absolute path to the sessions directory.

    Returns:
        pathlib.Path: ``<cwd>/.janito/sessions``.
    """
    return Path.cwd() / SESSIONS_DIR


def session_file_path(session_id: str) -> Path:
    """Return the jsonl file path for a session id."""
    return get_sessions_dir() / f"{session_id}.jsonl"


def _session_meta(session) -> dict[str, Any]:
    """Serialize the session's metadata line (everything but ``messages``)."""
    return {
        "session_id": session.session_id,
        "title": session.title,
        "created_at": session.created_at,
        "last_active": session.last_active,
        "system_prompt": session.system_prompt,
    }


def save_session(session) -> None:
    """Rewrite ``<session_id>.jsonl`` with the session's metadata + messages.

    The file is rewritten in full (not appended) so rollbacks, restarts and
    mid-turn truncations are reflected on disk. Best-effort: never raises.
    """
    try:
        path = session_file_path(session.session_id)
        with _lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                f.write(json.dumps(_session_meta(session), ensure_ascii=False) + "\n")
                for msg in session.messages:
                    f.write(json.dumps(msg, ensure_ascii=False) + "\n")
    except Exception as e:  # noqa: BLE001 - persistence must never break the server
        logger.debug(f"Failed to save session {session.session_id}: {e}")


def delete_session_file(session_id: str) -> bool:
    """Remove the session's jsonl file.

    Returns:
        bool: ``True`` if a file was removed, ``False`` otherwise. Never raises.
    """
    try:
        path = session_file_path(session_id)
        with _lock:
            if path.exists():
                path.unlink()
                return True
            return False
    except Exception as e:  # noqa: BLE001 - persistence must never break the server
        logger.debug(f"Failed to delete session file {session_id}: {e}")
        return False


def _read_session_file(path: Path) -> dict[str, Any] | None:
    """Parse one session file into a ``{meta..., "messages": [...]}`` dict.

    Returns ``None`` (and logs) for empty, malformed or unreadable files;
    individual malformed message lines are skipped so one bad line does not
    discard the whole conversation.
    """
    try:
        with _lock:
            with path.open("r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f if ln.strip()]
        if not lines:
            return None
        meta = json.loads(lines[0])
        if not isinstance(meta, dict) or "session_id" not in meta:
            logger.debug(f"Skipping session file without metadata: {path}")
            return None

        messages: list[dict[str, Any]] = []
        for line in lines[1:]:
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                logger.debug(f"Skipping malformed message line in {path}: {line!r}")
                continue
            if isinstance(msg, dict):
                messages.append(msg)

        meta["messages"] = messages
        return meta
    except Exception as e:  # noqa: BLE001 - persistence must never break the server
        logger.debug(f"Failed to read session file {path}: {e}")
        return None


def load_sessions() -> list[dict[str, Any]]:
    """Read every ``.janito/sessions/*.jsonl`` file.

    Returns:
        list[dict]: One ``{session_id, title, created_at, last_active,
        system_prompt, messages}`` dict per readable file, sorted by file
        name. Malformed/unreadable files are skipped with a debug log. Never
        raises.
    """
    sessions: list[dict[str, Any]] = []
    try:
        directory = get_sessions_dir()
        if not directory.exists():
            return sessions
        for path in sorted(directory.glob("*.jsonl")):
            parsed = _read_session_file(path)
            if parsed is not None:
                sessions.append(parsed)
    except Exception as e:  # noqa: BLE001 - persistence must never break the server
        logger.debug(f"Failed to load sessions from disk: {e}")
    return sessions


__all__ = [
    "SESSIONS_DIR",
    "get_sessions_dir",
    "session_file_path",
    "save_session",
    "delete_session_file",
    "load_sessions",
]
