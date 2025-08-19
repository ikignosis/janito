"""
Scripted runner for Janito chat mode.

This utility allows you to execute the interactive ``ChatSession`` logic with
an *in-memory* list of user inputs, making it much easier to write automated
unit or integration tests for the chat CLI without resorting to fragile
pseudo-terminal tricks.

The runner monkey-patches the private ``_handle_input`` method so that the
chat loop thinks it is receiving interactive input, while in reality the
values come from the provided list.  All output is captured through a
``rich.console.Console`` instance configured with ``record=True`` so the test
can later inspect the rendered text.

Typical usage
-------------
>>> from janito.cli.chat_mode.script_runner import ChatScriptRunner
>>> inputs = ["Hello!", "/exit"]
>>> runner = ChatScriptRunner(inputs)
>>> transcript = runner.run()
>>> assert "Hello!" in transcript

The ``ChatScriptRunner`` purposefully replaces the internal call to the agent
with a real agent call by default. If you want to use a stub, you must modify the runner implementation.
"""

from __future__ import annotations

from types import MethodType
from typing import List, Optional

from rich.console import Console

from janito.cli.chat_mode.session import ChatSession
from janito.provider_registry import ProviderRegistry
from janito.llm.driver_config import LLMDriverConfig

__all__ = ["ChatScriptRunner"]


auth_warning = (
    "[yellow]ChatScriptRunner is executing in stubbed-agent mode; no calls to an "
    "external LLM provider will be made.[/yellow]"
)


class ChatScriptRunner:
    """Run a **ChatSession** non-interactively using a predefined set of inputs."""

    def __init__(
        self,
        inputs: List[str],
        *,
        console: Optional[Console] = None,
        provider: str = "moonshot",
        model: str = "kimi-k1-8k",
        use_real_agent: bool = True,
        **chat_session_kwargs,
    ) -> None:
        """Create the runner.

        Parameters
        ----------
        inputs:
            Ordered list of strings that will be fed to the chat loop.
        console:
            Optional *rich* console.  If *None*, a new one is created with
            *record=True* so that output can later be retrieved through
            :py:meth:`rich.console.Console.export_text`.
        use_real_agent:
        chat_session_kwargs:
            Extra keyword arguments forwarded to :class:`janito.cli.chat_mode.session.ChatSession`.
        """
        self._input_queue = list(inputs)
        self.console = console or Console(record=True)
        self.provider = provider
        self.model = model
        self.use_real_agent = use_real_agent
        # Ensure we always pass a non-interactive *args* namespace so that the
        # normal ChatSession logic skips the Questionary profile prompt which
        # is incompatible with headless test runs.
        if "args" not in chat_session_kwargs or chat_session_kwargs["args"] is None:
            from types import SimpleNamespace

            chat_session_kwargs["args"] = SimpleNamespace(
                profile="developer",
                provider=self.provider,
                model=self.model,
            )

        # Create the ChatSession instance **after** we monkey-patch methods that rely on
        # prompt-toolkit so that no attempt is made to instantiate terminal UIs in
        # a headless environment like CI.

        # 1) Patch *ChatSession._create_prompt_session* to do nothing – the
        #    interactive session object is irrelevant for scripted runs.
        from types import MethodType as _MT

        if "_original_create_prompt_session" not in ChatSession.__dict__:
            ChatSession._original_create_prompt_session = ChatSession._create_prompt_session  # type: ignore[attr-defined]
        ChatSession._create_prompt_session = _MT(lambda _self: None, ChatSession)  # type: ignore[method-assign]

        # Resolve provider instance now so that ChatSession uses a ready agent
        provider_instance = ProviderRegistry().get_instance(self.provider)
        if provider_instance is None:
            raise RuntimeError(
                f"Provider '{self.provider}' is not available on this system."
            )
        driver_config = LLMDriverConfig(model=self.model)
        chat_session_kwargs.setdefault("provider_instance", provider_instance)
        chat_session_kwargs.setdefault("llm_driver_config", driver_config)

        self.chat_session = ChatSession(console=self.console, **chat_session_kwargs)

        # Monkey-patch the *ChatSession._handle_input* method so that it pops
        # from our in-memory queue instead of reading from stdin.
        def _script_handle_input(
            this: ChatSession, _prompt_session_unused
        ):  # noqa: D401
            if not self._input_queue:
                # Signal normal shutdown
                this._handle_exit()
                return None
            return self._input_queue.pop(0)

        # Bind the method to the *chat_session* instance.
        self.chat_session._handle_input = MethodType(  # type: ignore[assignment]
            _script_handle_input, self.chat_session
        )

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------
    def run(self) -> str:
        """Execute the chat session and return the captured transcript."""
        self.chat_session.run()
        return self.console.export_text()

    # ---------------------------------------------------------------------
    # Helpers to introspect results
    # ---------------------------------------------------------------------
    def get_history(self):
        """Return the structured conversation history produced by the LLM."""
        try:
            return self.chat_session.shell_state.conversation_history.get_history()
        except Exception:
            return []

    def get_last_response(self) -> str | None:
        """Return the *assistant* content of the last message, if any."""
        history = self.get_history()
        for message in reversed(history):
            if message.get("role") == "assistant":
                return message.get("content")
        return None

    # Convenience alias so tests can simply call *runner()*
    __call__ = run
