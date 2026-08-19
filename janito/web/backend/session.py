"""Conversation session management for the web backend."""

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field

from .config import WebServerConfig
from .session_store import delete_session_file, load_sessions, save_session

logger = logging.getLogger(__name__)


@dataclass
class ConversationSession:
    """A single conversation with its message history."""

    session_id: str
    messages: list[dict] = field(default_factory=list)
    system_prompt: str | None = None
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    title: str = "New conversation"
    # Provider/model selected for this conversation. Once the first user
    # message is sent these values are immutable for the lifetime of the
    # session, so switching tabs cannot silently change its context.
    provider: str | None = None
    model: str | None = None
    # Index into ``messages`` marking the last known-good state; cancel
    # (Ctrl+C) and error recovery truncate back to here.  Mirrors the
    # shell's ``history_checkpoint`` attribute.
    history_checkpoint: int = 0

    def touch(self) -> None:
        self.last_active = time.time()

    def restart(self) -> None:
        """Clear conversation history, preserving the system prompt.

        Mirrors the shell's F2 / ``restart`` behaviour: the system prompt
        is kept (so the AI retains its instructions) while all user/assistant
        messages are discarded.
        """
        if self.system_prompt:
            self.messages = [{"role": "system", "content": self.system_prompt}]
        else:
            self.messages = []
        # Checkpoint starts after the system prompt (if any)
        self.history_checkpoint = len(self.messages)
        self.touch()

    def to_summary(self) -> dict:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "message_count": len(self.messages),
            "created_at": self.created_at,
            "last_active": self.last_active,
            "provider": self.provider,
            "model": self.model,
            "has_messages": any(m.get("role") == "user" for m in self.messages),
        }

    def to_dict(self) -> dict:
        return {
            **self.to_summary(),
            "messages": self.messages,
            "system_prompt": self.system_prompt,
            "provider": self.provider,
            "model": self.model,
        }


class SessionManager:
    """Store of active sessions (TTL-based expiry), persisted to disk.

    Each session's conversation history is mirrored to
    ``./.janito/sessions/<session_id>.jsonl`` (see
    :mod:`janito.web.backend.session_store`) so conversations survive a
    server restart. Persistence is skipped entirely when
    ``config.no_history`` is set (``--no-history``).
    """

    def __init__(self, config: WebServerConfig, ttl_seconds: int = 3600):
        self.config = config
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, ConversationSession] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _persist(self, session: ConversationSession) -> None:
        """Write the session to disk unless ``--no-history`` was passed."""
        if self.config.no_history:
            return
        save_session(session)

    def load_from_disk(self) -> int:
        """Restore persisted sessions from ``.janito/sessions/``.

        Called once at server startup so conversations survive a restart.
        Returns the number of sessions restored (0 with ``--no-history``).
        """
        if self.config.no_history:
            return 0
        loaded = 0
        for meta in load_sessions():
            session = ConversationSession(
                session_id=meta["session_id"],
                messages=meta.get("messages", []),
                system_prompt=meta.get("system_prompt"),
                created_at=meta.get("created_at", time.time()),
                last_active=meta.get("last_active", time.time()),
                title=meta.get("title", "New conversation"),
                provider=meta.get("provider"),
                model=meta.get("model"),
            )
            # Checkpoint starts after the restored system prompt (if any), so
            # a cancel/error on the next turn rolls back only that turn.
            session.history_checkpoint = len(session.messages)
            with self._lock:
                self._sessions[session.session_id] = session
            loaded += 1
        if loaded:
            logger.info(f"Restored {loaded} session(s) from disk")
        return loaded

    def create(self) -> ConversationSession:
        """Create a new session with the effective system prompt."""
        session_id = uuid.uuid4().hex[:12]
        system_prompt = self.config.get_effective_system_prompt()

        messages: list[dict] = []
        if system_prompt and not self.config.no_system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        session = ConversationSession(
            session_id=session_id,
            messages=messages,
            system_prompt=system_prompt,
        )
        # Checkpoint starts after the system prompt (if any)
        session.history_checkpoint = len(messages)
        with self._lock:
            self._sessions[session_id] = session
        self._persist(session)
        return session

    def get(self, session_id: str) -> ConversationSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
        if session:
            session.touch()
        return session

    def delete(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                removed = True
            else:
                removed = False
        if removed and not self.config.no_history:
            delete_session_file(session_id)
        return removed

    def list_sessions(self) -> list[ConversationSession]:
        with self._lock:
            return list(self._sessions.values())

    def set_title(self, session_id: str, title: str) -> bool:
        session = self.get(session_id)
        if session:
            session.title = title[:120]
            self._persist(session)
            return True
        return False

    def persist(self, session: ConversationSession) -> None:
        """Persist a session's current state (called after each turn).

        The chat router calls this after a turn completes — normally, on
        cancel (rollback), on error (rollback), and after a restart — so
        the on-disk jsonl always mirrors the in-memory conversation.
        """
        self._persist(session)

    def cleanup_expired(self) -> int:
        """Remove sessions idle longer than TTL. Returns count removed."""
        now = time.time()
        expired = []
        with self._lock:
            for sid, session in self._sessions.items():
                if now - session.last_active > self.ttl_seconds:
                    expired.append(sid)
            for sid in expired:
                del self._sessions[sid]
        return len(expired)
