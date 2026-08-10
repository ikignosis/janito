"""Pluggable user-prompt handler for interactive tools (web mode).

Tools that need interactive input (e.g. the AskUser tool) call
``BaseTool.prompt_user``, which by default renders the question in a Rich
table and reads the answer from stdin. In web mode there is no console, so
the web backend installs a *prompt handler* through the context variable
below: the handler presents the question as a modal in the browser and
returns the answer typed by the user.

This mirrors the design of :mod:`janito.tooling.reporter`: a ``ContextVar``
that defaults to ``None`` (console behaviour) and accessor functions the web
backend uses to install/restore a handler for the duration of a turn.
``asyncio.to_thread`` copies the current context into the worker thread that
executes the tool, so a handler installed on the async side is visible to
``prompt_user`` running inside the tool.
"""

from collections.abc import Callable
from contextvars import ContextVar

# A prompt handler receives a question (str) and returns the user's answer
# (str). ``None`` means "no handler installed" -> the CLI stdin fallback in
# BaseTool.prompt_user applies.
PromptHandler = Callable[[str], str]

_prompt_handler: ContextVar[PromptHandler | None] = ContextVar(
    "_prompt_handler", default=None
)


def set_prompt_handler(handler: PromptHandler | None) -> None:
    """Install a prompt handler for the current async context.

    Pass ``None`` to restore the default console-based prompting.
    """
    _prompt_handler.set(handler)


def get_prompt_handler() -> PromptHandler | None:
    """Return the currently installed prompt handler, or ``None``."""
    return _prompt_handler.get()
