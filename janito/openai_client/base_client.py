"""
Shared agent-loop pipeline for the API client modules.

The four clients (``completions_api``, ``conversations_api``,
``anthropic_api`` and ``dashscope_api``) each implemented the same ~300-line
turn pipeline: clear the changes log, reset the used-files tracker, resolve
the runtime config, create the SDK client, load MCP tools, build the
:class:`~janito.tooling.executor.ToolExecutor`, resolve the model settings,
then loop *stream -> display -> tool calls -> finalize*.

This module extracts that pipeline into a :class:`Client` base class as a
template method (:meth:`send`).  Subclasses implement the API-specific hooks;
the module-level ``send_prompt`` functions remain as thin wrappers that
construct the subclass and call :meth:`send`, so existing call sites (the
interactive shell, ``cli/chat.py`` and the tests) are unaffected.

Test-coupling note
------------------
The tests monkeypatch module-level names in each client module
(``resolve_runtime_config``, ``_run_with_progress_bar``, ``OpenAI``,
``ToolExecutor``, ``get_all_tool_schemas``, ...).  A function's globals are
looked up in the module it is *defined* in, so every hook that can be
monkeypatched must resolve through the **subclass module's** global
namespace at call time.  That is why each subclass implements its hooks as
thin forwarders to its own module's globals instead of the base importing
those names directly (e.g. ``CompletionsClient._resolve_runtime_config``
calls the ``resolve_runtime_config`` global of ``completions_api``).
"""

import logging
from typing import Any

from rich.console import Console

from janito.config_store import get_config_value
from janito.general_config import get_active_provider
from janito.tooling.changes import clear_changes
from janito.tooling.used_files import reset_used_files

from .client_support import (
    _display_content,
    _display_reasoning,
    _display_usage,
    _load_mcp,
    _print_verbose_info,
)

# Configure logger for this module
logger = logging.getLogger(__name__)


class Client:
    """Shared agent-loop pipeline for a single API backend.

    Subclasses implement the API-specific hooks; :meth:`send` runs the common
    turn pipeline (template method).  The class is stateless across turns: the
    per-call values (SDK client, resolved config, conversation state) are
    locals of :meth:`send` and are threaded into the hooks explicitly, so a
    single client instance can be reused for many prompts.

    Attributes:
        cli_model: Model passed via ``--model`` (overrides the provider's config).
        cli_provider: Provider passed via ``--provider`` (overrides config/auth).
        reasoning_level: Reasoning depth passed via ``--reasoning-level``.
        use_mcp: Whether to load and use MCP tools.
        api_type: Canonical API type name (e.g. ``"Completions"``).
        backend_default: Fallback backend label for verbose output when
            ``base_url`` is ``None``.
    """

    #: Canonical API type name (e.g. ``"Completions"``, ``"Responses"``).
    api_type: str = "Completions"

    #: Fallback backend label shown in verbose mode when ``base_url`` is None.
    backend_default: str = "api.openai.com"

    def __init__(
        self,
        cli_model: str | None = None,
        cli_provider: str | None = None,
        reasoning_level: str | None = None,
        use_mcp: bool = True,
    ) -> None:
        self.cli_model = cli_model
        self.cli_provider = cli_provider
        self.reasoning_level = reasoning_level
        self.use_mcp = use_mcp

    # ------------------------------------------------------------------
    # Template method: the shared turn pipeline
    # ------------------------------------------------------------------

    def send(
        self,
        prompt: str,
        *,
        verbose: bool = False,
        tools: list[dict[str, Any]] | None = None,
        thinking: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Run one full turn: setup, stream loop, tool calls, finalize.

        ``kwargs`` carries the conversation-context parameters of the concrete
        ``send_prompt`` signature (e.g. ``previous_messages``,
        ``previous_response_id``, ``previous_items``, ``instructions``); each
        subclass's :meth:`_init_conversation_state` picks the ones it needs.

        Returns:
            The API-specific turn result: the assistant text (``str``) for the
            stateless clients, or a ``ConversationResult`` for the Responses
            client.
        """
        # Reset per-prompt tracking so ./janito/changes.jsonl and the
        # "Used files" report only describe the current prompt.
        clear_changes()
        reset_used_files()

        base_url, api_key, model = self._resolve_runtime_config()
        client = self._create_sdk_client(base_url, api_key)
        logger.debug(f"{type(self).__name__} client created with base_url={base_url}")

        # Initialize MCP manager and load services if enabled; the tool
        # executor routes tool calls to the MCP manager or the built-in
        # registry and tracks usage/used-files/changes around each call.
        mcp_manager, mcp_tools = _load_mcp(self.use_mcp)
        tool_executor = self._create_tool_executor(mcp_manager)
        tools_schemas = self._resolve_tools(tools, mcp_tools)

        logger.debug(f"Using {len(tools_schemas)} tools total")

        provider = self._active_provider()
        (
            thinking,
            max_output_tokens,
            max_input_tokens,
            reasoning_level,
        ) = self._resolve_model_settings(
            provider, model, thinking, self.reasoning_level
        )
        preserve_thinking = self._get_config("preserve_thinking")
        if preserve_thinking is not None:
            logger.debug(f"Using preserve_thinking from config: {preserve_thinking}")

        console = Console()

        # Print model and backend info only in verbose mode
        if verbose:
            self._print_verbose_info(console, base_url, model, mcp_manager)

        # Conversation-state model depends on the client (client-owned
        # messages list vs server-side response id vs client-side items).
        state = self._init_conversation_state(prompt, provider, model, **kwargs)

        while True:
            # Build the base call parameters for one round.
            call_kwargs = self._build_call_kwargs(
                model,
                state,
                max_output_tokens,
                reasoning_level,
                preserve_thinking,
                thinking,
            )

            # Consume the full stream under a progress bar (the blocking work
            # runs in a worker thread via the module's _run_with_progress_bar
            # while the main thread drives the spinner).
            (
                full_content,
                reasoning_content,
                tool_calls,
                usage_info,
            ) = self._run_stream_round(
                client,
                call_kwargs,
                tools_schemas,
                state,
                base_url=base_url,
                api_key=api_key,
                model=model,
                console=console,
            )

            logger.debug("API streaming response completed")
            _display_reasoning(reasoning_content, console)

            # Display the assembled response using rich markdown
            _display_content(full_content, console)

            # Check if the model wants to call tools
            if tool_calls:
                # Record the assistant's tool calls, execute every call and
                # append the tool responses to the history, then loop to get
                # the final response after the tool calls.
                state = self._handle_tool_calls(
                    tool_calls, full_content, reasoning_content, state, tool_executor
                )
                continue

            # No more tool calls, return the final response.
            return self._finalize(
                full_content,
                reasoning_content,
                state,
                usage_info,
                max_input_tokens,
                max_output_tokens,
                console,
            )

    # ------------------------------------------------------------------
    # Shared helpers (base implementation; not monkeypatched by tests)
    # ------------------------------------------------------------------

    def _active_provider(self) -> str:
        """The provider in effect: ``--provider`` or the configured default."""
        return self.cli_provider or get_active_provider()

    def _get_config(self, key: str) -> Any:
        """Read a config value (e.g. ``preserve_thinking``)."""
        return get_config_value(key)

    def _print_verbose_info(self, console, base_url, model, mcp_manager) -> None:
        """Print model/backend/MCP info in verbose mode."""
        _print_verbose_info(console, base_url, model, mcp_manager, self.backend_default)

    # ------------------------------------------------------------------
    # Hooks every subclass must implement (forwarding to its module globals)
    # ------------------------------------------------------------------

    def _resolve_runtime_config(self):
        """Resolve ``(base_url, api_key, model)`` (module-global forwarder)."""
        raise NotImplementedError

    def _create_sdk_client(self, base_url, api_key):
        """Create the SDK client (module-global forwarder, e.g. ``OpenAI``)."""
        raise NotImplementedError

    def _create_tool_executor(self, mcp_manager):
        """Create the ToolExecutor (module-global forwarder)."""
        raise NotImplementedError

    def _resolve_tools(self, tools, mcp_tools):
        """Resolve the tool schemas (built-in + MCP), API-specific format."""
        raise NotImplementedError

    def _resolve_model_settings(self, provider, model, thinking, reasoning_level):
        """Resolve ``(thinking, max_output_tokens, max_input_tokens, reasoning_level)``
        for the resolved ``model``."""
        raise NotImplementedError

    def _init_conversation_state(self, prompt, provider, model, **kwargs):
        """Build the per-turn conversation state from ``**kwargs``."""
        raise NotImplementedError

    def _build_call_kwargs(
        self,
        model,
        state,
        max_output_tokens,
        reasoning_level,
        preserve_thinking,
        thinking,
    ):
        """Build the API call parameters for one round."""
        raise NotImplementedError

    def _run_stream_round(
        self,
        client,
        call_kwargs,
        tools_schemas,
        state,
        *,
        base_url,
        api_key,
        model,
        console,
    ):
        """Run one streaming round; return ``(content, reasoning, tool_calls, usage)``.

        This hook owns the module's ``_run_with_progress_bar`` / ``_stream_response``
        wiring and the API-specific exception handling.
        """
        raise NotImplementedError

    def _handle_tool_calls(
        self, tool_calls, full_content, reasoning_content, state, tool_executor
    ):
        """Record + execute tool calls; return the updated conversation state."""
        raise NotImplementedError

    def _finalize(
        self,
        full_content,
        reasoning_content,
        state,
        usage_info,
        max_input_tokens,
        max_output_tokens,
        console,
    ):
        """Record the final assistant message, print reports and return the result."""
        raise NotImplementedError


# Re-export the shared display helper used by subclasses' finalizers so the
# module is a single import point for the common client machinery.
__all__ = [
    "Client",
    "_display_usage",
]
