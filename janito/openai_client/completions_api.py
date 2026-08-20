"""
OpenAI client module for sending prompts to OpenAI-compatible endpoints.
Uses streaming (SSE) to display tokens as they arrive.
"""

import logging
import sys
import threading
from typing import Any

from openai import AuthenticationError, NotFoundError, OpenAI
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import auth handling (API keys come from the auth store, not the environment)
from janito.auth_config import get_api_key

# Import general configuration handling
from janito.config_loaders import load_endpoint_from_config, load_model_from_config
from janito.general_config import load_provider_from_config

# Import provider configuration for base URLs and built-in defaults
from ..provider_accessors import (
    get_default_model_from_provider,
    requires_explicit_model,
)
from ..provider_validation import is_custom_provider

# Import the tool executor (routes tool calls to the MCP manager or the
# built-in registry and tracks usage/used-files/changes around each call)
from ..tooling.executor import ToolExecutor

# Shared agent-loop pipeline (see Client.send) implemented by CompletionsClient.
from .base_client import Client

# Shared helpers reused by every client module (token formatting, MCP
# loading, Rich console output, auth-error explainer) and the Chat
# Completions stream consumer.  Re-exported here so existing
# ``completions_api.<name>`` references (including tests) keep working.
from .client_support import (  # noqa: F401 (re-exported for backward compat)
    _display_content,
    _display_reasoning,
    _display_usage,
    _handle_auth_error,
    _load_mcp,
    _print_verbose_info,
    format_tokens,
)
from .completions_helpers import (
    _build_call_kwargs,
    _finalize_response,
    _handle_not_found_error,
    _resolve_model_settings,
    _resolve_tools,
)
from .completions_stream import (  # noqa: F401 (re-exported for backward compat)
    _consume_chunk,
    _consume_stream,
    _consume_tool_call_delta,
    _stream_response,
)

# Import tools

# Import used-files tracking (best-effort, never fails)


# Configure logger for this module
logger = logging.getLogger(__name__)


def resolve_runtime_config(
    cli_model: str | None = None,
    cli_provider: str | None = None,
    cli_api_type: str | None = None,
) -> tuple[str | None, str, str]:
    """
    Resolve the runtime configuration (base_url, api_key, model) without
    relying on OPENAI_* environment variables.

    Resolution rules:
      - api_key:  taken from the auth store (~/.janito/auth.json) for the
                  active provider (see ``auth_config.get_api_key``).
      - base_url: the endpoint configured for the provider (``--set endpoint``)
                  or, when none is set, the provider's built-in default base
                  URL resolved for the effective API type (see
                  ``provider_accessors.get_endpoint_for_api_type``, honoring the
                  provider's ``endpoint_by_api_type`` map). ``None`` means the
                  standard OpenAI endpoint.
      - model:    ``--model`` (``cli_model``) when given, otherwise the model
                  configured for the active provider (``<provider>.model``),
                  and finally the provider's built-in default model.  A
                  provider whose built-in default is the ``"custom"``
                  placeholder (e.g. ``openrouter``) has no usable default --
                  the placeholder only carries built-in defaults such as the
                  default API type -- so the user must supply the model
                  explicitly (``--model`` or ``<provider>.model``) and an
                  unresolvable model is reported as an error.

    Args:
        cli_model: Model passed via ``--model`` (highest priority). May be None.
        cli_provider: Provider passed via ``--provider``. May be None.
        cli_api_type: API type passed via ``--api-type`` (or implied by the
            selected client, e.g. ``"Anthropic"`` for the native Anthropic
            SDK). Used to pick the built-in default endpoint when the provider
            declares ``endpoint_by_api_type``. May be None.

    Returns:
        Tuple of (base_url, api_key, model). ``base_url`` may be None for the
        standard OpenAI API.

    Raises:
        ValueError: If the API key or model cannot be resolved, or if a custom
            provider has no endpoint configured.
    """
    # Provider: --provider CLI arg, then config.json.  The default provider
    # is stored under the ``provider`` key in config.json -- never in
    # auth.json.  If none of these is set, report that no provider is
    # configured rather than silently assuming "openai".
    provider = cli_provider or load_provider_from_config()
    if not provider:
        logger.error("No provider configured")
        raise ValueError(
            "No provider is configured. "
            "Set one with: janito --set provider=<name> (e.g. janito --set provider=alibaba) "
            "or pass --provider <name>."
        )
    logger.debug(f"Resolving runtime config for provider: {provider}")

    # API key from the auth store (no environment variables).
    api_key = get_api_key(provider)
    if not api_key:
        logger.error(f"No API key configured for provider '{provider}'")
        raise ValueError(
            f"No API key configured for provider '{provider}'. "
            f"Set one with: janito --set-api-key <key> --provider {provider}"
        )

    # Model: --model, then the provider's configured model, and finally the
    # provider's built-in default model (from the provider config).  A
    # provider whose built-in default is the "custom" placeholder (e.g.
    # "openrouter") has no usable default: the placeholder "custom" model
    # entry only carries built-in defaults (the default API type), so the
    # user must supply the model explicitly (--model or <provider>.model in
    # config.json).  When it cannot be resolved, report it here instead of
    # silently sending the placeholder to the API.
    model = cli_model or load_model_from_config(provider)
    if not model:
        model = get_default_model_from_provider(provider)
        if model and requires_explicit_model(provider):
            model = None
    if not model:
        logger.error(f"No model configured for provider '{provider}'")
        raise ValueError(
            f"No model configured for provider '{provider}'. "
            f"Pass --model <name> or set it with: "
            f"janito --provider {provider} --set model=<name>"
        )

    # Base URL: configured endpoint for the provider, otherwise the provider's
    # built-in default resolved for the effective API type (None for standard
    # OpenAI). The effective API type comes from --api-type, then the
    # provider's configured api-type, then its built-in default.
    base_url = load_endpoint_from_config(provider)
    if not base_url:
        if is_custom_provider(provider):
            logger.warning(f"Custom provider '{provider}' has no endpoint configured")
            raise ValueError(
                f"Provider '{provider}' requires an endpoint. "
                f"Set it with: janito --provider {provider} --set endpoint=<url>"
            )
        from ..general_config import resolve_api_type
        from ..provider_accessors import get_endpoint_for_api_type

        api_type = resolve_api_type(cli_api_type, provider)
        base_url = get_endpoint_for_api_type(provider, api_type)

    logger.debug(f"Runtime config resolved: base_url={base_url}, model={model}")
    return base_url, api_key, model


def get_env_config() -> tuple[str | None, str, str]:
    """Backward-compatible alias for :func:`resolve_runtime_config`.

    Retained for external callers; resolves configuration from auth/config
    without using environment variables.
    """
    return resolve_runtime_config()


class RequestCancelled(Exception):
    """Raised when the user cancels a pending API request by pressing Enter.

    Unlike ``KeyboardInterrupt`` (Ctrl+C), which rolls the conversation
    history back to the last checkpoint, this signals an *interrupt without
    rollback*: the user's message stays in the conversation history so the
    conversation can continue from where it was interrupted.

    Attributes:
        partial_result: The worker thread's return value, when it finished
            honouring the cancel before the exception was raised (e.g. the
            stream consumers return the partially-assembled response parts,
            from which a server-side response id can be recovered). ``None``
            when the worker was still busy.
    """

    def __init__(self, message: str = "Request cancelled by user (pressed Enter)."):
        super().__init__(message)
        self.partial_result = None


def _is_enter_pressed() -> bool:
    """Return True if the user pressed Enter on stdin (non-blocking).

    Only meaningful when stdin is an interactive TTY; returns False for
    piped/redirected input so streamed data is never consumed here.

    POSIX: after prompt_toolkit's prompt ends, the terminal is back in
    canonical mode, so a full line (i.e. an Enter press) becomes available at
    once; ``select`` reports readability and ``readline`` consumes the line.

    Windows: ``msvcrt.kbhit``/``getwch`` report the raw key press.
    """
    if not sys.stdin.isatty():
        return False
    try:
        if sys.platform == "win32":
            import msvcrt

            if msvcrt.kbhit():
                key = msvcrt.getwch()
                if key in ("\r", "\n"):
                    # Drain any keys buffered after the Enter press.
                    while msvcrt.kbhit():
                        msvcrt.getwch()
                    return True
                return False
            return False
        import select

        if select.select([sys.stdin], [], [], 0)[0]:
            # A full line is available in canonical mode => Enter was pressed.
            sys.stdin.readline()
            return True
        return False
    except Exception:
        # Never let input detection break the request flow.
        return False


def _run_with_progress_bar(func, *args, **kwargs):
    """Run a function with a Rich progress bar in a separate thread.

    While the worker runs, stdin is polled non-blockingly for an Enter press:
    if the user presses Enter, the in-flight request is aborted through a
    shared ``cancel_event`` and :class:`RequestCancelled` is raised (an
    interrupt without rolling the conversation history back, unlike Ctrl+C).
    """
    result = [None]
    exception = [None]
    cancel_event = threading.Event()

    def target():
        try:
            result[0] = func(*args, **kwargs, cancel_event=cancel_event)
        except Exception as e:
            exception[0] = e

    # Create and start the thread
    thread = threading.Thread(target=target)
    thread.start()

    # Show progress bar while waiting
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task(
            "Waiting for response from the API server...", total=None
        )
        while thread.is_alive():
            if _is_enter_pressed():
                cancel_event.set()
                break
            progress.update(task, advance=0.1)
            thread.join(timeout=0.1)

    cancelled = cancel_event.is_set()
    if not cancelled:
        thread.join()
    else:
        # Give the worker a moment to honour the cancel (break out of the
        # stream and close the connection); if it is stuck in the initial
        # connect it finishes in the background, mirroring Ctrl+C behaviour.
        thread.join(timeout=2.0)

    if cancelled:
        if exception[0]:
            logger.debug("Worker exception while cancelling request: %s", exception[0])
        exc = RequestCancelled("Request cancelled by user (pressed Enter).")
        # Keep the worker's partial return value (e.g. the aborted response's
        # id) so callers can carry the conversation forward without losing
        # the user's message.
        exc.partial_result = result[0]
        raise exc
    if exception[0]:
        raise exception[0]
    return result[0]


def send_prompt(
    prompt: str,
    verbose: bool = False,
    previous_messages: list[dict[str, Any]] = None,
    tools: list[dict[str, Any]] | None = None,
    use_mcp: bool = True,
    thinking: bool = False,
    cli_model: str | None = None,
    cli_provider: str | None = None,
    reasoning_level: str | None = None,
) -> str:
    """Send prompt to OpenAI endpoint and return response using streaming.

    Args:
        prompt: The user prompt to send
        verbose: If True, print model and backend info
        previous_messages: List of previous message dicts for conversation context
        tools: Optional list of tool schemas to pass. If None, uses all available tools.
               If an empty list, no tools are passed.
        use_mcp: If True, load and use MCP tools (default True)
        thinking: If True, enable thinking mode (extra_body={'enable_thinking':
            True}). When False (default), falls back to the provider's built-in
            default, which is True for DeepSeek and Alibaba/Qwen.
        cli_model: Model passed via ``--model`` (overrides the provider's config).
        cli_provider: Provider passed via ``--provider`` (overrides config/auth).
        reasoning_level: Reasoning depth passed via ``--reasoning-level``
            (overrides the provider's configured value and built-in default).
            Sent to the API as ``reasoning_effort``.
    """
    logger.info("Sending prompt to API")
    return CompletionsClient(
        cli_model=cli_model,
        cli_provider=cli_provider,
        reasoning_level=reasoning_level,
        use_mcp=use_mcp,
    ).send(
        prompt,
        verbose=verbose,
        previous_messages=previous_messages,
        tools=tools,
        thinking=thinking,
    )


class CompletionsClient(Client):
    """Chat Completions client (``client.chat.completions.create``).

    The conversation history is owned **client-side**: the caller-owned
    ``previous_messages`` list is mutated in place (user/assistant turns are
    appended), so the interactive shell's history keeps growing.  Every hook
    forwards to this module's globals so test monkeypatches keep working.
    """

    api_type = "Completions"

    def _resolve_runtime_config(self):
        return resolve_runtime_config(self.cli_model, self.cli_provider)

    def _create_sdk_client(self, base_url, api_key):
        # base_url can be None for standard OpenAI
        return OpenAI(api_key=api_key, base_url=base_url)

    def _create_tool_executor(self, mcp_manager):
        return ToolExecutor(mcp_manager)

    def _resolve_tools(self, tools, mcp_tools):
        return _resolve_tools(tools, mcp_tools)

    def _resolve_model_settings(self, provider, model, thinking, reasoning_level):
        return _resolve_model_settings(provider, model, thinking, reasoning_level)

    def _init_conversation_state(self, prompt, provider, model, **kwargs):
        # Use previous messages if provided, otherwise start with the user
        # prompt.  NOTE: check `is not None` (not truthiness). An empty list
        # is a valid, caller-owned history (e.g. after a restart or with
        # --no-system-prompt); using a truthy check would replace it with a
        # new local list and the appended messages would never propagate back
        # to the caller, silently resetting the history on every turn.
        previous_messages = kwargs.get("previous_messages")
        messages = previous_messages if previous_messages is not None else []
        messages.append({"role": "user", "content": prompt})
        return messages

    def _build_call_kwargs(
        self,
        model,
        state,
        max_output_tokens,
        reasoning_level,
        preserve_thinking,
        thinking,
    ):
        # The effective model's built-in tools (e.g. Alibaba/Qwen's
        # code_interpreter / web_search / web_extractor) are resolved for
        # the effective provider and sent as request-body enable_* flags in
        # extra_body (see completions_helpers._build_call_kwargs).  They are
        # resolved for the Completions API type, so API types without
        # built-in tools (e.g. alibaba's qwen3.8-max) send nothing.
        from janito.provider_accessors import get_default_tools_from_provider

        tools = get_default_tools_from_provider(
            self._active_provider(), model, api_type="Completions"
        )
        return _build_call_kwargs(
            model,
            state,
            max_output_tokens,
            reasoning_level,
            preserve_thinking,
            thinking,
            tools,
            provider=self._active_provider(),
        )

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
        try:
            (
                full_content,
                reasoning_content,
                tool_calls,
                usage_info,
                raw_attrs,
            ) = _run_with_progress_bar(
                _stream_response, client, call_kwargs, tools_schemas
            )
        except NotFoundError as e:
            _handle_not_found_error(e, base_url, model, console)
            raise
        except AuthenticationError as e:
            _handle_auth_error(e, self.cli_provider, api_key, base_url, model, console)
            raise
        return full_content, reasoning_content, tool_calls, usage_info, raw_attrs

    def _handle_tool_calls(
        self, tool_calls, full_content, reasoning_content, state, tool_executor
    ):
        # Build the assistant message (with tool_calls), execute every call
        # and append the tool responses to the history, then loop to get the
        # final response after the tool calls.
        tool_executor.handle_tool_calls(tool_calls, state, full_content)
        return state

    def _finalize(
        self,
        full_content,
        reasoning_content,
        state,
        usage_info,
        max_input_tokens,
        max_output_tokens,
        console,
        provider=None,
        model=None,
    ):
        return _finalize_response(
            full_content,
            reasoning_content,
            state,
            usage_info,
            max_input_tokens,
            max_output_tokens,
            console,
            provider=provider,
            model=model,
        )
