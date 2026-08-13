"""In-browser user prompting for the web agent (AskUser tool).

The AskUser tool's ``prompt_user`` normally reads from stdin; in web mode
there is no console. The web backend instead installs a
:class:`WebPromptHandler` (via :func:`janito.tooling.prompting.set_prompt_handler`)
that presents the question in a non-blocking inline card in the browser
chat and waits for the answer:

1. the tool runs in a worker thread (``asyncio.to_thread``) and calls
   ``prompt_user``, which invokes the installed handler synchronously;
2. the handler registers a :class:`PendingPrompt` in the connection's
   :class:`PromptRegistry`, schedules a ``{"type": "prompt", ...}`` message
   on the WebSocket (via ``run_coroutine_threadsafe``) and blocks the worker
   thread on the prompt's event;
3. the WebSocket receive loop (``_await_cancel`` in ``routers/chat.py``)
   resolves the prompt when the browser posts
   ``{"type": "prompt_answer", ...}``;
4. the worker thread wakes up and returns the answer to the tool.

The registry is created once per WebSocket connection in
``routers/chat.chat_websocket`` and shared by the receive loop and the
prompt handler, so multiple concurrent questions per connection (e.g. two
AskUser calls in one turn) each get their own ``prompt_id``.
"""

import asyncio
import threading
import uuid
from typing import Any


class PendingPrompt:
    """A question waiting for the browser's answer (thread-safe)."""

    __slots__ = ("prompt_id", "question", "_event", "answer", "cancelled")

    def __init__(self, prompt_id: str, question: str) -> None:
        self.prompt_id = prompt_id
        self.question = question
        self._event = threading.Event()
        self.answer: str | None = None
        self.cancelled = False

    def resolve(self, answer: str) -> None:
        """Store the answer and wake the waiting worker thread."""
        self.answer = answer
        self._event.set()

    def cancel(self) -> None:
        """Wake the waiter without an answer (turn ended / disconnected)."""
        self.cancelled = True
        self._event.set()

    def wait(self, timeout: float | None = None) -> bool:
        """Block until resolved or cancelled. Returns True when done."""
        return self._event.wait(timeout)


class PromptRegistry:
    """Per-WebSocket-connection registry of pending in-browser questions."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: dict[str, PendingPrompt] = {}

    def register(self, prompt_id: str, question: str) -> PendingPrompt:
        """Add a pending prompt and return its handle."""
        pending = PendingPrompt(prompt_id, question)
        with self._lock:
            self._pending[prompt_id] = pending
        return pending

    def resolve(self, prompt_id: str, answer: str) -> bool:
        """Resolve a pending prompt by id. Returns False when unknown."""
        with self._lock:
            pending = self._pending.pop(prompt_id, None)
        if pending is None:
            return False
        pending.resolve(answer)
        return True

    def cancel_all(self) -> int:
        """Wake every still-pending prompt as cancelled. Returns count."""
        with self._lock:
            pending = list(self._pending.values())
            self._pending.clear()
        for item in pending:
            item.cancel()
        return len(pending)

    def has_pending(self) -> bool:
        """True when at least one question is still awaiting an answer."""
        with self._lock:
            return bool(self._pending)


class WebPromptHandler:
    """Synchronous prompt callback that shows an inline browser question card.

    Runs inside the worker thread that executes the tool. It registers a
    :class:`PendingPrompt`, asks the event loop to push the question to the
    browser chat and blocks the thread until the receive loop resolves it. A
    failed send (socket died) or a cancelled turn resolves as an empty
    answer so the worker thread never hangs.
    """

    # How long to wait for the ``prompt`` frame to actually be sent before
    # assuming the socket is dead. The send itself is fast; this only
    # matters for a broken connection.
    _SEND_TIMEOUT = 5.0

    def __init__(
        self,
        websocket: Any,
        loop: asyncio.AbstractEventLoop,
        registry: PromptRegistry,
    ) -> None:
        self._websocket = websocket
        self._loop = loop
        self._registry = registry

    def __call__(self, question: str) -> str:
        prompt_id = uuid.uuid4().hex
        pending = self._registry.register(prompt_id, question)

        try:
            send = asyncio.run_coroutine_threadsafe(
                self._send_prompt(prompt_id, question), self._loop
            )
            send.result(timeout=self._SEND_TIMEOUT)
        except Exception:
            # The socket is dead / the loop closed: nothing will ever answer
            # this question. Wake the waiter so the tool returns empty.
            self._registry.cancel_all()
            pending.wait()
            return ""

        pending.wait()
        return pending.answer or ""

    async def _send_prompt(self, prompt_id: str, question: str) -> None:
        await self._websocket.send_json(
            {"type": "prompt", "prompt_id": prompt_id, "question": question}
        )


__all__ = [
    "PendingPrompt",
    "PromptRegistry",
    "WebPromptHandler",
]
