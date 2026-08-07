"""
OpenAI client module for sending prompts to OpenAI-compatible endpoints.
Uses streaming (SSE) to display tokens as they arrive.
"""

import logging
import sys
import threading
from typing import Any

from openai import AuthenticationError, NotFoundError, OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import auth handling (API keys come from the auth store, not the environment)
from janito.auth_config import get_api_key, get_default_provider

# Import general configuration handling
from janito.general_config import (
    get_active_provider,
    get_config_value,
    get_masked_api_key,
    load_endpoint_from_config,
    load_max_output_tokens,
    load_model_from_config,
    load_provider_from_config,
    load_reasoning_level,
)

# Import MCP manager
from ..mcp_manager import get_mcp_manager

# Import provider configuration for base URLs and built-in defaults
from ..provider_config import (
    get_default_max_input_tokens_from_provider,
    get_default_max_output_tokens_from_provider,
    get_default_model_from_provider,
    get_default_reasoning_level_from_provider,
    get_default_thinking_from_provider,
    is_custom_provider,
)
from ..tooling.changes import clear_changes

# Import the tool executor (routes tool calls to the MCP manager or the
# built-in registry and tracks usage/used-files/changes around each call)
from ..tooling.executor import ToolExecutor

# Import tools
from ..tooling.tools_registry import get_all_tool_schemas

# Import used-files tracking (best-effort, never fails)
from ..tooling.used_files import format_used_files, reset_used_files

# Configure logger for this module
logger = logging.getLogger(__name__)


class RequestCancelled(Exception):
    """Raised when the user cancels a pending API request by pressing Enter.

    Unlike ``KeyboardInterrupt`` (Ctrl+C), which rolls the conversation
    history back to the last checkpoint, this signals an *interrupt without
    rollback*: the user's message stays in the conversation history so the
    conversation can continue from where it was interrupted.
    """


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


def format_tokens(count):
    """Convert a token count to a human-readable format.

    Examples:
        2000 -> "2k"
        4000000 -> "4m"
        150 -> "150"
        12345 -> "12.3k"
    """
    if count is None:
        return None
    try:
        value = float(count)
    except (TypeError, ValueError):
        return count

    def _format(number):
        # Trim trailing ".0" for whole numbers (e.g. "2.0k" -> "2k")
        if number == int(number):
            return str(int(number))
        return f"{number:.1f}"

    if value >= 1_000_000:
        return f"{_format(value / 1_000_000)}m"
    if value >= 1_000:
        return f"{_format(value / 1_000)}k"
    return str(int(value))


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
                  ``provider_config.get_endpoint_for_api_type``, honoring the
                  provider's ``endpoint_by_api_type`` map). ``None`` means the
                  standard OpenAI endpoint.
      - model:    ``--model`` (``cli_model``) when given, otherwise the model
                  configured for the active provider (``<provider>.model``),
                  and finally the provider's built-in default model.

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
    # Provider: --provider CLI arg, then config.json, then auth.json default.
    # If none of these is set, report that no provider is configured rather
    # than silently assuming "openai".
    provider = cli_provider or load_provider_from_config() or get_default_provider()
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
    # provider's built-in default model (from PROVIDER_INFO).
    model = cli_model or load_model_from_config(provider)
    if not model:
        model = get_default_model_from_provider(provider)
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
        from ..provider_config import get_endpoint_for_api_type

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


def _run_with_progress_bar(func, *args, **kwargs):
    """Run a function with a Rich progress bar in a separate thread.

    While the worker runs, stdin is polled non-blockingly for an Enter press:
    if the user presses Enter, the in-flight request is aborted through a
    shared ``cancel_event`` and :class:`RequestCancelled` is raised (an
    interrupt without rolling the conversation history back).
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
        raise RequestCancelled("Request cancelled by user (pressed Enter).")
    if exception[0]:
        raise exception[0]
    return result[0]


def _consume_stream(stream, cancel_event=None):
    """Consume a streaming completion and assemble the response parts.

    Returns ``(full_content, reasoning_content, tool_calls_map, usage_info)``.

    When ``cancel_event`` is set (user pressed Enter while waiting), the
    stream is abandoned as soon as the next chunk arrives.
    """
    collected_content: list[str] = []
    collected_reasoning: list[str] = []
    tool_calls_map: dict[int, dict[str, str]] = {}  # index -> {id, name, arguments}
    usage_info = None

    for chunk in stream:
        # Honour an Enter-to-cancel request: stop consuming as soon as the
        # next chunk arrives so the worker can close the connection.
        if cancel_event is not None and cancel_event.is_set():
            break

        # Usage stats arrive in the final chunk when include_usage is set
        if hasattr(chunk, "usage") and chunk.usage:
            usage_info = chunk.usage

        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta

        # Collect reasoning / thinking content (DeepSeek R1, OpenAI o1/o3, …)
        for attr in ("reasoning_content", "reasoning"):
            val = getattr(delta, attr, None)
            if val:
                collected_reasoning.append(val)
                break

        # Accumulate main content silently
        if delta.content:
            collected_content.append(delta.content)

        # Accumulate tool-call deltas (split across many chunks)
        if hasattr(delta, "tool_calls") and delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in tool_calls_map:
                    tool_calls_map[idx] = {"id": "", "name": "", "arguments": ""}
                if tc_delta.id:
                    tool_calls_map[idx]["id"] = tc_delta.id
                if tc_delta.function:
                    if tc_delta.function.name:
                        tool_calls_map[idx]["name"] = tc_delta.function.name
                    if tc_delta.function.arguments:
                        tool_calls_map[idx]["arguments"] += tc_delta.function.arguments

    full_content = "".join(collected_content)
    reasoning_content = "".join(collected_reasoning) if collected_reasoning else None
    return full_content, reasoning_content, tool_calls_map, usage_info


def _stream_response(client, call_kwargs, tools_schemas, cancel_event=None):
    """Open a streaming completion and fully consume it.

    Returns ``(full_content, reasoning_content, tool_calls_map, usage_info)``.

    When ``cancel_event`` is set (user pressed Enter while waiting), the
    stream is abandoned and the underlying connection is closed.
    """
    if tools_schemas:
        logger.debug(f"Calling API (streaming) with {len(tools_schemas)} tools")
        stream = client.chat.completions.create(
            **call_kwargs,
            tools=tools_schemas,
            tool_choice="auto",
        )
    else:
        logger.debug("Calling API (streaming) without tools")
        stream = client.chat.completions.create(**call_kwargs)

    try:
        return _consume_stream(stream, cancel_event=cancel_event)
    finally:
        # Abort the underlying HTTP stream when the user pressed Enter so the
        # connection is released promptly instead of streaming to completion.
        if cancel_event is not None and cancel_event.is_set():
            stream.close()


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
    # Remove any changes log from a previous prompt so ./janito/changes.jsonl
    # only describes the changes made while handling the current prompt.
    clear_changes()
    # Clear the in-process used-files tracker so the end-of-prompt
    # "Used files" report only describes files touched while handling the
    # *current* prompt instead of accumulating across the whole session.
    reset_used_files()
    base_url, api_key, model = resolve_runtime_config(cli_model, cli_provider)

    # Create OpenAI client - base_url can be None for standard OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)

    logger.debug(f"OpenAI client created with base_url={base_url}")

    # Initialize MCP manager and load services if enabled
    mcp_manager = None
    if use_mcp:
        mcp_manager = get_mcp_manager()
        try:
            mcp_manager.load_services()
            mcp_tools = mcp_manager.get_all_tools()
            logger.info(
                f"Loaded {len(mcp_tools)} MCP tools from {len(mcp_manager.connected_services)} services"
            )
        except Exception as e:
            logger.warning(f"Failed to load MCP tools: {e}")
            mcp_tools = []
    else:
        mcp_tools = []

    # Tool executor routes tool calls to the MCP manager or the built-in
    # registry and tracks usage/used-files/changes around each call.
    tool_executor = ToolExecutor(mcp_manager)

    # Get available tools if not explicitly provided
    if tools is None:
        # Merge built-in tools with MCP tools
        built_in_tools = get_all_tool_schemas()
        tools_schemas = built_in_tools + mcp_tools
        logger.debug(
            f"Using {len(built_in_tools)} built-in tools + {len(mcp_tools)} MCP tools"
        )
    else:
        tools_schemas = tools
        logger.debug(f"Using {len(tools_schemas)} provided tools")

    logger.debug(f"Using {len(tools_schemas)} tools total")

    # Load max output tokens from general config if set
    provider = cli_provider or get_active_provider()

    # Thinking mode: the explicit --thinking flag wins, otherwise the
    # provider's built-in default applies (True for DeepSeek and Alibaba/Qwen,
    # which reason by default). See provider_config.PROVIDER_INFO.
    if not thinking:
        thinking = get_default_thinking_from_provider(provider)
    max_output_tokens = load_max_output_tokens(provider)
    if max_output_tokens is None:
        # Fall back to the provider's built-in default (from PROVIDER_INFO),
        # then to a global default of 100k tokens.
        max_output_tokens = get_default_max_output_tokens_from_provider(provider)
    if max_output_tokens is None:
        max_output_tokens = 100000  # default to 100k tokens if not set in config

    # Load the provider's built-in max input tokens (context window) for the
    # usage summary display.
    max_input_tokens = get_default_max_input_tokens_from_provider(provider)

    # Reasoning level (reasoning_effort): --reasoning-level CLI arg, then the
    # provider's configured value (--set reasoning-level=...), and finally the
    # provider's built-in default (from PROVIDER_INFO, e.g. "xhigh" for
    # Alibaba's qwen3.8-max). None means the API's own default applies.
    reasoning_level = reasoning_level or load_reasoning_level(provider)
    if reasoning_level is None:
        reasoning_level = get_default_reasoning_level_from_provider(provider)

    # Check for preserve_thinking in config
    preserve_thinking = get_config_value("preserve_thinking")
    if preserve_thinking is not None:
        logger.debug(f"Using preserve_thinking from config: {preserve_thinking}")

    console = Console()

    # Print model and backend info only in verbose mode
    if verbose:
        backend = base_url if base_url else "api.openai.com"
        from rich.text import Text

        text = Text(f"----- Model: {model} | Backend: {backend}")
        text.stylize("white on blue")
        console.print(text, highlight=False)

        # Show MCP status in verbose mode
        if mcp_manager and mcp_manager.connected_services:
            services_text = Text(
                f"----- MCP Services: {', '.join(mcp_manager.connected_services)}"
            )
            services_text.stylize("white on green")
            console.print(services_text, highlight=False)

    # Use previous messages if provided, otherwise start with the user prompt.
    # NOTE: check `is not None` (not truthiness). An empty list is a valid,
    # caller-owned history (e.g. after a restart or with --no-system-prompt);
    # using a truthy check would replace it with a new local list and the
    # appended messages would never propagate back to the caller, silently
    # resetting the conversation history on every turn.
    messages = previous_messages if previous_messages is not None else []
    messages.append({"role": "user", "content": prompt})

    logger.debug(f"Starting message loop with {len(messages)} messages")

    while True:
        # Build the base call parameters
        call_kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 1.0,
        }

        # Add max_tokens if max output tokens is set in config
        if max_output_tokens is not None:
            call_kwargs["max_completion_tokens"] = max_output_tokens

        # Pass the reasoning level (reasoning_effort) when resolved (from
        # --reasoning-level, per-provider config, or the built-in default).
        if reasoning_level:
            call_kwargs["reasoning_effort"] = reasoning_level

        # Pass preserve_thinking in extra_body if defined in config
        if preserve_thinking is not None:
            if "extra_body" not in call_kwargs:
                call_kwargs["extra_body"] = {}
            call_kwargs["extra_body"]["preserve_thinking"] = preserve_thinking

        # Pass enable_thinking in extra_body if thinking flag is set
        if thinking:
            if "extra_body" not in call_kwargs:
                call_kwargs["extra_body"] = {}
            call_kwargs["extra_body"]["enable_thinking"] = True

        # ------ Streaming API call ------
        call_kwargs["stream"] = True
        call_kwargs["stream_options"] = {"include_usage": True}

        # Consume the full stream under a progress bar. The blocking work
        # (connection setup + full response generation) runs in a worker thread
        # via _run_with_progress_bar while the main thread drives the spinner,
        # mirroring the pre-streaming behaviour where the spinner covered the
        # entire request.
        try:
            (
                full_content,
                reasoning_content,
                tool_calls_map,
                usage_info,
            ) = _run_with_progress_bar(
                _stream_response, client, call_kwargs, tools_schemas
            )
        except NotFoundError as e:
            if "Model not exist" in str(e) or "model not exist" in str(e).lower():
                api_url = base_url if base_url else "https://api.openai.com"
                console.print(
                    f"[bold red]Error: Model not found.[/bold red] "
                    f"Current model being used: [bold]{model}[/bold] | API URL: [bold]{api_url}[/bold]"
                )
                console.print(
                    "[dim]Please check that the model name is correct and available "
                    "for your API key/provider.[/dim]"
                )
                logger.error(f"Model '{model}' not found at API URL '{api_url}': {e}")
            raise
        except AuthenticationError as e:
            provider = cli_provider or get_active_provider()
            masked_key = get_masked_api_key(api_key)
            api_url = base_url if base_url else "https://api.openai.com"
            console.print(
                "[bold red]Error: Authentication failed (invalid API key).[/bold red]"
            )
            console.print(f"  Provider: [bold]{provider}[/bold]")
            console.print(f"  Model:    [bold]{model}[/bold]")
            console.print(f"  API URL:  [bold]{api_url}[/bold]")
            console.print(f"  API Key:  [bold]{masked_key}[/bold]")
            console.print(
                f"[dim]Please verify your API key for the '{provider}' provider "
                f"and try again.[/dim]"
            )
            logger.error(
                f"Authentication failed - provider: {provider}, model: {model}, "
                f"api_url: {api_url}, api_key: {masked_key}: {e}"
            )
            raise

        logger.debug("API streaming response completed")
        if reasoning_content:
            from rich.panel import Panel

            console.print(
                Panel(
                    Markdown(reasoning_content),
                    title="[bold cyan]\U0001f4ad Reasoning[/bold cyan]",
                    border_style="cyan",
                    padding=(1, 2),
                )
            )
            logger.debug("Reasoning content displayed")

        # Display the assembled response using rich markdown
        if full_content:
            console.print(Markdown(full_content))

        # Check if the model wants to call tools
        if tool_calls_map:
            # Build the assistant message (with tool_calls), execute every
            # call and append the tool responses to the history, then loop to
            # get the final response after the tool calls.
            tool_executor.handle_tool_calls(tool_calls_map, messages, full_content)
            continue
        else:
            # No more tool calls, return the final response
            # Build the assistant message with reasoning_content if available
            assistant_message = {"role": "assistant", "content": full_content}
            if reasoning_content:
                assistant_message["reasoning_content"] = reasoning_content

            # Add assistant message to conversation history
            messages.append(assistant_message)

            # Display the tracked used files before the token usage summary.
            # Nothing is printed when no files were tracked (empty Text).
            used_files_report = format_used_files()
            if used_files_report:
                console.print(used_files_report, highlight=False)

            # Display token usage with magenta background
            if usage_info:
                total_tokens = getattr(usage_info, "total_tokens", None)
                input_tokens = getattr(usage_info, "prompt_tokens", None)
                output_tokens = getattr(usage_info, "completion_tokens", None)
                cached_tokens = None
                if (
                    hasattr(usage_info, "prompt_tokens_details")
                    and usage_info.prompt_tokens_details
                ):
                    cached_tokens = getattr(
                        usage_info.prompt_tokens_details, "cached_tokens", None
                    )

                from rich.text import Text

                parts = []
                if total_tokens is not None:
                    parts.append(f"Total: {format_tokens(total_tokens)}")
                if input_tokens is not None:
                    if max_input_tokens is not None:
                        parts.append(
                            f"In: {format_tokens(input_tokens)}/{format_tokens(max_input_tokens)}"
                        )
                    else:
                        parts.append(f"In: {format_tokens(input_tokens)}")
                if output_tokens is not None:
                    if max_output_tokens is not None:
                        parts.append(
                            f"Out: {format_tokens(output_tokens)}/{format_tokens(max_output_tokens)}"
                        )
                    else:
                        parts.append(f"Out: {format_tokens(output_tokens)}")
                if cached_tokens is not None:
                    parts.append(f"Cached: {format_tokens(cached_tokens)}")
                parts.append(f"Messages: {len(messages)}")

                token_text = Text(f"=== {' | '.join(parts)} ===")
                token_text.stylize("white on magenta")
                console.print(token_text, highlight=False)
                logger.info(
                    f"Request completed: total={total_tokens} tokens "
                    f"(in={input_tokens}, out={output_tokens}, "
                    f"cached={cached_tokens}, max={max_output_tokens}), "
                    f"{len(messages)} messages"
                )
            return full_content
