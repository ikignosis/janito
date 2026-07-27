"""Conversation session management for the web backend."""

import threading
import time
import uuid
from dataclasses import dataclass, field

from .config import WebServerConfig


@dataclass
class ConversationSession:
    """A single conversation with its message history."""

    session_id: str
    messages: list[dict] = field(default_factory=list)
    system_prompt: str | None = None
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    title: str = "New conversation"

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
        self.touch()

    def to_summary(self) -> dict:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "message_count": len(self.messages),
            "created_at": self.created_at,
            "last_active": self.last_active,
        }

    def to_dict(self) -> dict:
        return {
            **self.to_summary(),
            "messages": self.messages,
            "system_prompt": self.system_prompt,
        }


class SessionManager:
    """In-memory store of active sessions (TTL-based expiry)."""

    def __init__(self, config: WebServerConfig, ttl_seconds: int = 3600):
        self.config = config
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, ConversationSession] = {}
        self._lock = threading.Lock()

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
        with self._lock:
            self._sessions[session_id] = session
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
                return True
            return False

    def list_sessions(self) -> list[ConversationSession]:
        with self._lock:
            return list(self._sessions.values())

    def set_title(self, session_id: str, title: str) -> bool:
        session = self.get(session_id)
        if session:
            session.title = title[:120]
            return True
        return False

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
