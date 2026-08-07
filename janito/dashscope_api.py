"""
DashScope SDK client module for sending prompts through the **native**
DashScope SDK (``dashscope.Generation.call``).

This is the counterpart of :mod:`janito.openai_client.completions_api` for the
``"DashScope"`` API type: the same config resolution, tool loading, MCP
support, progress spinner, Enter-to-cancel, reasoning panel, used-files report
and token-usage summary, but talking to the DashScope native API through the
official ``dashscope`` package instead of an OpenAI-compatible endpoint.

The ``dashscope`` package is **optional**: the API type is only accepted by
``--set api-type=DashScope`` when the package is installed
(``provider_config.REQUIRES_BY_API_TYPE``), and this module refuses to run
without it, with an actionable install message.  Because the package may be
absent, the import happens lazily inside :func:`_create_client` (checked with
``importlib.util.find_spec``, mirroring the web-mode extra check) rather than
at module import time, so importing ``janito`` never requires ``dashscope``.

Like the Completions implementation, this module owns the conversation
history **client-side**: the DashScope generation API is stateless, so every
turn re-sends the full ``messages`` list.  Tool calls are executed with the
shared :class:`~janito.tooling.executor.ToolExecutor` and their ``tool``-role
messages are appended to the history before the next round, repeating until
the model emits a final text answer.  ``send_prompt`` returns the assistant
text and mutates ``previous_messages`` in place (Completions-style), so the
interactive shell treats this mode exactly like Completions.

Unlike the OpenAI-compatible types, the DashScope SDK talks to the **native**
DashScope API (``https://dashscope-intl.aliyuncs.com/api/v1`` for the
international region).  The base URL is a module-level global on the
``dashscope`` package (``dashscope.base_http_api_url``); it is set from the
provider's ``endpoint_by_api_type`` map (or a config endpoint override) before
each call.
"""

from __future__ import annotations

import importlib.util
import logging
import re
from types import SimpleNamespace
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

# Import general configuration handling
from janito.general_config import (
    get_active_provider,
    get_masked_api_key,
    load_max_output_tokens,
)

# Import MCP manager
from janito.mcp_manager import get_mcp_manager

# Shared helpers reused from the Chat Completions implementation so all
# client modules stay in sync: runtime config resolution, token formatting,
# the progress spinner / Enter-to-cancel runner and the request-cancelled
# signal.
from janito.openai_client.completions_api import (
    RequestCancelled,
    _run_with_progress_bar,
    format_tokens,
    resolve_runtime_config,
)

# Import provider configuration for built-in defaults
from janito.provider_config import (
    get_default_max_input_tokens_from_provider,
    get_default_max_output_tokens_from_provider,
    get_default_thinking_from_provider,
)

# Import the tool executor (routes tool calls to the MCP manager or the
# built-in registry and tracks usage/used-files/changes around each call)
from janito.tooling.changes import clear_changes
from janito.tooling.executor import ToolExecutor

# Import tools
from janito.tooling.tools_registry import get_all_tool_schemas

# Import used-files tracking (best-effort, never fails)
from janito.tooling.used_files import format_used_files, reset_used_files

# Configure logger for this module
logger = logging.getLogger(__name__)


class _ModelEndpointMismatch(RuntimeError):
    """Raised when the DashScope API rejects a model for the chosen endpoint.

    The native DashScope API serves models from two generation endpoints:
    ``text-generation`` (``Generation.call``) for plain-text models and
    ``multimodal-generation`` (``MultiModalConversation.call``) for multimodal
    models.  Sending a model to the wrong endpoint fails with
    ``InvalidParameter: url error, please check url``.  ``_stream_response``
    catches this to retry once on the other endpoint.
    """


def _is_multimodal_model(model: str) -> bool:
    """Return True when a DashScope model is served by the multimodal endpoint.

    The DashScope native API serves plain-text models (``qwen-plus``,
    ``qwen-flash``, ``qwen3-max``, ``qwen3.7-max``, ...) from the
    ``text-generation`` endpoint (``Generation.call``) and multimodal models
    (Qwen-VL / Qwen-Omni, the ``qwen3.x-plus`` generation, and the
    ``qwen3.8-max`` flagship) from the ``multimodal-generation`` endpoint
    (``MultiModalConversation.call``).  Calling a model on the wrong endpoint
    fails with ``InvalidParameter: url error, please check url``.

    This is a best-effort heuristic: when it misclassifies a model,
    ``_stream_response`` retries once on the other endpoint.
    """
    name = (model or "").strip().lower()
    if not name:
        return False
    # Vision / omni model families are multimodal by naming convention.
    if "-vl" in name or "omni" in name:
        return True
    # The qwen3.x-plus generation and the qwen3.8-max flagship are served by
    # the multimodal-generation endpoint, while the qwen3.x-max text models
    # (e.g. qwen3.7-max) are not.
    if re.match(r"^qwen3\.\d+-plus$", name) or name == "qwen3.8-max":
        return True
    return False


def _to_multimodal_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert plain-string message content to DashScope multimodal form.

    The multimodal-generation API expects every message ``content`` to be a
    list of modality items (``[{"text": "..."}]``) instead of a plain string.
    Returns a shallow copy with string contents wrapped; other fields
    (``tool_calls``, ``tool_call_id``, ``reasoning_content``) are kept as-is.
    """
    converted = []
    for message in messages:
        message = dict(message)
        content = message.get("content")
        if isinstance(content, str):
            message["content"] = [{"text": content}]
        converted.append(message)
    return converted


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read a key from a DashScope SDK object (DictMixin: dict- or attr-style).

    The DashScope SDK response/message objects are ``DictMixin`` instances,
    which support both attribute access (``resp.output``) and mapping access
    (``resp["output"]``).  Some fields (e.g. ``tool_calls``) are plain dicts.
    This helper abstracts over both so the stream consumer stays robust.
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _create_client(base_url: str | None, api_key: str) -> SimpleNamespace:
    """Prepare the native DashScope SDK client, guarding the optional package.

    The ``dashscope`` package is optional (see
    ``provider_config.REQUIRES_BY_API_TYPE``), so its availability is checked
    explicitly with ``importlib.util.find_spec`` (mirroring the web-mode extra
    check) and the import happens lazily -- importing ``janito`` never
    requires ``dashscope``.

    The DashScope SDK is stateless at the module level: the base URL is a
    module global (``dashscope.base_http_api_url``) and the API key is passed
    per call.  This helper therefore returns a lightweight handle carrying
    the resolved ``base_url`` / ``api_key`` for the call loop instead of a
    client object.

    Args:
        base_url: The native-SDK base URL (from the provider's
            ``endpoint_by_api_type`` map or a config endpoint override).
        api_key: The API key from the auth store.

    Returns:
        A ``SimpleNamespace`` with ``base_url`` and ``api_key``.

    Raises:
        RuntimeError: If the ``dashscope`` package is not installed, with an
            actionable install message.
    """
    if importlib.util.find_spec("dashscope") is None:
        raise RuntimeError(
            "API type 'DashScope' requires the optional 'dashscope' package, "
            "which is not installed. Install it with: pip install dashscope"
        )
    import dashscope

    # The DashScope SDK routes requests through the module-level
    # ``base_http_api_url`` global.  Point it at the resolved endpoint (the
    # provider's native-SDK base URL, or a config endpoint override) before
    # the first call; the API key is passed per call below.
    if base_url:
        dashscope.base_http_api_url = base_url
        logger.debug(f"DashScope base_http_api_url set to {base_url}")

    return SimpleNamespace(base_url=base_url, api_key=api_key)


def _consume_stream(stream, cancel_event=None):
    """Consume a streaming DashScope generation response.

    Works for both the text-generation (``Generation.call``) and
    multimodal-generation (``MultiModalConversation.call``) streams.

    Returns ``(full_content, reasoning_content, tool_use_blocks, usage_info)``
    where ``tool_use_blocks`` is a list of
    ``{"id", "name", "arguments"}`` dicts (``arguments`` is the raw JSON
    string from the model) and ``usage_info`` is a ``SimpleNamespace`` with
    ``total_tokens``/``input_tokens``/``output_tokens`` (``None`` when the
    API reported no usage).

    With ``incremental_output=True`` (set by the caller) each chunk carries
    only the newly generated text, so content / reasoning deltas are
    accumulated.  Multimodal responses carry ``content`` as a list of
    modality items (``[{"text": "..."}]``), which is joined here.  The
    terminal chunk reports ``finish_reason == "stop"``; tool-call requests
    stream across many chunks (the ``arguments`` JSON is split), so they are
    accumulated by ``index``.

    When ``cancel_event`` is set (user pressed Enter while waiting), the
    stream is abandoned as soon as the next chunk arrives.
    """
    collected_content: list[str] = []
    collected_reasoning: list[str] = []
    tool_calls_map: dict[int, dict[str, str]] = {}  # index -> {id, name, arguments}
    input_tokens = None
    output_tokens = None
    total_tokens = None
    chunks_seen = 0

    for chunk in stream:
        chunks_seen += 1
        # Honour an Enter-to-cancel request: stop consuming as soon as the
        # next chunk arrives so the worker can close the connection.
        if cancel_event is not None and cancel_event.is_set():
            break

        status_code = _get(chunk, "status_code")
        if status_code is not None and status_code != 200:
            code = _get(chunk, "code") or ""
            message = _get(chunk, "message") or "DashScope API error"
            request_id = _get(chunk, "request_id") or ""
            detail = f" (request_id={request_id})" if request_id else ""
            if code == "InvalidParameter" and "url error" in message:
                # The model was sent to the wrong generation endpoint
                # (multimodal vs text).  Signal the caller to retry once on
                # the other endpoint.
                raise _ModelEndpointMismatch(
                    f"DashScope API error (code={code}): {message}{detail}"
                )
            raise RuntimeError(f"DashScope API error (code={code}): {message}{detail}")

        output = _get(chunk, "output") or {}
        choices = _get(output, "choices") or []
        if not choices:
            # Keep consuming: the terminal chunk may still carry usage.
            usage = _get(chunk, "usage")
            if usage is not None:
                input_tokens = _get(usage, "input_tokens", input_tokens)
                output_tokens = _get(usage, "output_tokens", output_tokens)
                total_tokens = _get(usage, "total_tokens", total_tokens)
            continue

        choice = choices[0]
        message = _get(choice, "message") or {}

        content = _get(message, "content") or ""
        if isinstance(content, list):
            # Multimodal responses carry content as a list of modality items
            # (e.g. [{"text": "..."}]); join the text parts.
            content = "".join(
                item.get("text", "") for item in content if isinstance(item, dict)
            )
        if content:
            collected_content.append(content)

        reasoning = _get(message, "reasoning_content") or ""
        if reasoning:
            collected_reasoning.append(reasoning)

        # Tool-call requests stream across many chunks: each chunk carries a
        # partial tool_call with an ``index`` and the ``arguments`` JSON is
        # split across chunks, so accumulate by index (mirroring the
        # Completions consumer) instead of appending one block per chunk.
        for tc in _get(message, "tool_calls") or []:
            idx = _get(tc, "index", 0) or 0
            entry = tool_calls_map.setdefault(
                idx, {"id": "", "name": "", "arguments": ""}
            )
            if _get(tc, "id"):
                entry["id"] = _get(tc, "id")
            function = _get(tc, "function") or {}
            if _get(function, "name"):
                entry["name"] = _get(function, "name")
            arguments = _get(function, "arguments")
            if arguments:
                entry["arguments"] += arguments

        # Keep the most recent usage reported by the API (streaming chunks
        # carry it on the final chunk).
        usage = _get(chunk, "usage")
        if usage is not None:
            input_tokens = _get(usage, "input_tokens", input_tokens)
            output_tokens = _get(usage, "output_tokens", output_tokens)
            total_tokens = _get(usage, "total_tokens", total_tokens)

        if _get(choice, "finish_reason") == "stop":
            break

    tool_use_blocks = [
        {
            "id": tool_calls_map[idx]["id"],
            "name": tool_calls_map[idx]["name"],
            "arguments": tool_calls_map[idx]["arguments"] or "{}",
        }
        for idx in sorted(tool_calls_map)
    ]
    full_content = "".join(collected_content)
    reasoning_content = "".join(collected_reasoning) if collected_reasoning else None
    # A healthy stream always ends with a chunk whose finish_reason is "stop";
    # a stream with zero chunks means the API failed before producing
    # anything.  Fail loudly instead of returning an empty answer.  An
    # Enter-to-cancel short-circuit must not be treated as an empty stream.
    if chunks_seen == 0 and (cancel_event is None or not cancel_event.is_set()):
        raise RuntimeError(
            "The DashScope API returned no stream chunks (empty response)."
        )
    usage_info = None
    if (
        input_tokens is not None
        or output_tokens is not None
        or total_tokens is not None
    ):
        usage_info = SimpleNamespace(
            total_tokens=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    return full_content, reasoning_content, tool_use_blocks, usage_info


def _stream_response(client, call_kwargs, tools_schemas, cancel_event=None):
    """Open a streaming DashScope generation call and fully consume it.

    Returns ``(full_content, reasoning_content, tool_use_blocks, usage_info)``.
    Tool schemas are attached here (mirroring ``completions_api._stream_response``);
    the caller builds the remaining kwargs per round.

    The native DashScope API serves multimodal models (e.g. the alibaba
    default ``qwen3.8-max``) from the ``multimodal-generation`` endpoint
    (``MultiModalConversation``) and plain-text models from
    ``text-generation`` (``Generation``).  The endpoint is inferred from the
    model name; when the API rejects the model with the "url error"
    (model/endpoint mismatch), the call is retried once on the other
    endpoint so misclassified models still work.

    When ``cancel_event`` is set (user pressed Enter while waiting), the
    stream is abandoned and the underlying connection is closed.
    """
    from dashscope import Generation, MultiModalConversation

    kwargs = dict(call_kwargs)
    kwargs["api_key"] = client.api_key
    if tools_schemas:
        logger.debug(
            f"Calling DashScope Generation API (streaming) with {len(tools_schemas)} tools"
        )
        kwargs["tools"] = tools_schemas
    else:
        logger.debug("Calling DashScope Generation API (streaming) without tools")

    multimodal = _is_multimodal_model(kwargs.get("model", ""))
    attempts = (multimodal, not multimodal)

    for use_multimodal in attempts:
        round_kwargs = dict(kwargs)
        if use_multimodal:
            # The multimodal API expects message content as a list of
            # modality items ([{"text": "..."}]) instead of a plain string.
            round_kwargs["messages"] = _to_multimodal_messages(round_kwargs["messages"])
        cls = MultiModalConversation if use_multimodal else Generation
        logger.debug(
            "Calling DashScope %s API (streaming) with %d tools",
            "multimodal-generation" if use_multimodal else "text-generation",
            len(tools_schemas),
        )
        stream = cls.call(**round_kwargs)
        try:
            try:
                return _consume_stream(stream, cancel_event=cancel_event)
            except _ModelEndpointMismatch:
                # The API rejected the model for this endpoint; retry once on
                # the other one, unless the user already pressed Enter.
                if cancel_event is not None and cancel_event.is_set():
                    raise
                if use_multimodal == attempts[-1]:
                    raise
                logger.debug(
                    "DashScope rejected the model for this endpoint; "
                    "retrying on the other generation endpoint"
                )
                continue
        finally:
            # Abort the underlying HTTP stream when the user pressed Enter so
            # the connection is released promptly instead of streaming to
            # completion.
            if cancel_event is not None and cancel_event.is_set():
                close = getattr(stream, "close", None)
                if callable(close):
                    close()


def send_prompt(
    prompt: str,
    verbose: bool = False,
    previous_messages: list[dict[str, Any]] | None = None,
    instructions: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    use_mcp: bool = True,
    thinking: bool = False,
    cli_model: str | None = None,
    cli_provider: str | None = None,
    reasoning_level: str | None = None,
) -> str:
    """Send a prompt through the native DashScope SDK and return the answer.

    Mirrors :func:`completions_api.send_prompt` (same config resolution, tool
    loading, spinner, reasoning panel, used-files report and usage summary)
    but targets the DashScope native generation API.  The conversation
    history is owned **client-side**: ``previous_messages`` is mutated in
    place (user and assistant turns are appended) so the interactive shell's
    history keeps growing, exactly like Completions mode.

    Args:
        prompt: The user prompt to send
        verbose: If True, print model and backend info
        previous_messages: List of previous message dicts for conversation
            context (mutated in place).  DashScope accepts ``system``-role
            messages directly, so no extraction is needed (unlike the
            Anthropic Messages API).
        instructions: Accepted for signature parity with the other clients.
            DashScope takes the system prompt as a ``system``-role message in
            ``messages``; when provided as a string it is prepended as one.
        tools: Optional list of tool schemas to pass. If None, uses all
            available tools. If an empty list, no tools are passed.
        use_mcp: If True, load and use MCP tools (default True)
        thinking: If True, enable thinking mode (``enable_thinking=True``).
            When False (default), falls back to the provider's built-in
            default, which is True for Alibaba/Qwen.
        cli_model: Model passed via ``--model`` (overrides the provider's config).
        cli_provider: Provider passed via ``--provider`` (overrides config/auth).
        reasoning_level: Accepted for signature parity with the other clients.
            The native DashScope SDK does not use ``reasoning_effort``
            (thinking depth is controlled by ``thinking_budget``, which is not
            wired yet).

    Returns:
        The assistant's final text (after any tool-call rounds).

    Raises:
        RuntimeError: If the ``dashscope`` package is not installed.
    """
    logger.info("Sending prompt to DashScope API (native SDK)")
    # Remove any changes log from a previous prompt so ./janito/changes.jsonl
    # only describes the changes made while handling the current prompt.
    clear_changes()
    # Clear the in-process used-files tracker so the end-of-prompt
    # "Used files" report only describes files touched while handling the
    # *current* prompt instead of accumulating across the whole session.
    reset_used_files()
    # This module is the "DashScope" API type, so endpoint resolution picks
    # the native-SDK base URL from the provider's endpoint_by_api_type map.
    base_url, api_key, model = resolve_runtime_config(
        cli_model, cli_provider, cli_api_type="DashScope"
    )
    client = _create_client(base_url, api_key)

    logger.debug(f"DashScope client prepared with base_url={base_url}")

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

    provider = cli_provider or get_active_provider()

    # Thinking mode: the explicit --thinking flag wins, otherwise the
    # provider's built-in default applies (True for Alibaba/Qwen, which
    # reason by default). See provider_config.PROVIDER_INFO.
    if not thinking:
        thinking = get_default_thinking_from_provider(provider)

    # Max output tokens: the resolved value (config > provider built-in
    # default > 100k) is sent as the DashScope ``max_tokens`` parameter.
    max_output_tokens = load_max_output_tokens(provider)
    if max_output_tokens is None:
        max_output_tokens = get_default_max_output_tokens_from_provider(provider)
    if max_output_tokens is None:
        max_output_tokens = 100000  # default to 100k tokens if not set in config

    # Load the provider's built-in max input tokens (context window) for the
    # usage summary display.
    max_input_tokens = get_default_max_input_tokens_from_provider(provider)

    console = Console()

    # Print model and backend info only in verbose mode
    if verbose:
        backend = base_url if base_url else "https://dashscope-intl.aliyuncs.com/api/v1"
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

    # Build the conversation.  Unlike the Anthropic Messages API, DashScope
    # accepts ``system``-role messages directly, so the history is sent
    # as-is; a string ``instructions`` value is prepended as a system message.
    messages = previous_messages if previous_messages is not None else []
    if instructions and not any(
        m.get("role") == "system" and m.get("content") for m in messages
    ):
        messages.insert(0, {"role": "system", "content": instructions})

    # NOTE: check `is not None` (not truthiness). An empty list is a valid,
    # caller-owned history (e.g. after a restart or with --no-system-prompt);
    # using a truthy check would replace it with a new local list and the
    # appended messages would never propagate back to the caller.
    messages.append({"role": "user", "content": prompt})

    logger.debug(f"Starting message loop with {len(messages)} messages")

    while True:
        # Build the base call parameters.  The DashScope native API is
        # stateless and the full history is re-sent on every round.
        call_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_output_tokens,
            "result_format": "message",
            "stream": True,
            "incremental_output": True,
        }
        # Enable thinking mode for Qwen models that support it (Alibaba/Qwen
        # reason by default).  Only set when True so models that always
        # reason keep their own default.
        if thinking:
            call_kwargs["enable_thinking"] = True

        # ------ Streaming API call ------
        # Consume the full stream under a progress bar. The blocking work
        # (connection setup + full response generation) runs in a worker thread
        # via _run_with_progress_bar while the main thread drives the spinner,
        # mirroring the completions_api behaviour.
        try:
            (
                full_content,
                reasoning_content,
                tool_use_blocks,
                usage_info,
            ) = _run_with_progress_bar(
                _stream_response, client, call_kwargs, tools_schemas
            )
        except Exception as e:
            # The dashscope SDK raises its own exception types; format the
            # common authentication failure with the same actionable details
            # as the OpenAI clients (the exception is always re-raised).
            status_code = getattr(e, "status_code", None)
            code = getattr(e, "code", None)
            if status_code == 401 or (
                isinstance(code, str) and "InvalidApiKey" in code
            ):
                masked_key = get_masked_api_key(api_key)
                console.print(
                    "[bold red]Error: Authentication failed (invalid API key).[/bold red]"
                )
                console.print(f"  Provider: [bold]{provider}[/bold]")
                console.print(f"  Model:    [bold]{model}[/bold]")
                console.print(f"  API URL:  [bold]{base_url}[/bold]")
                console.print(f"  API Key:  [bold]{masked_key}[/bold]")
                console.print(
                    f"[dim]Please verify your API key for the '{provider}' provider "
                    f"and try again.[/dim]"
                )
                logger.error(
                    f"Authentication failed - provider: {provider}, model: {model}, "
                    f"api_url: {base_url}, api_key: {masked_key}: {e}"
                )
            raise

        logger.debug("DashScope streaming response completed")
        if reasoning_content:
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
        if tool_use_blocks:
            # Record the assistant's message with its content and tool_calls
            # in the client-side history, then execute every call and send
            # the results back as tool-role messages before looping to get
            # the final answer.
            assistant_tool_calls = []
            for tc in tool_use_blocks:
                assistant_tool_calls.append(
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        },
                    }
                )
            assistant_message = {
                "role": "assistant",
                "content": full_content,
                "tool_calls": assistant_tool_calls,
            }
            if reasoning_content:
                assistant_message["reasoning_content"] = reasoning_content
            messages.append(assistant_message)

            for tc in tool_use_blocks:
                # Adapt the DashScope tool-use shape to what the executor
                # expects (id + function{name, arguments}).
                adapted_call = {
                    "id": tc["id"],
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"],
                    },
                }
                tool_message = tool_executor.execute_tool_call(adapted_call)
                messages.append(
                    {
                        "role": "tool",
                        "content": tool_message["content"],
                        "tool_call_id": tc["id"],
                    }
                )
            continue
        else:
            # No more tool calls, return the final response. Record the final
            # assistant text in the client-side history.
            assistant_message = {"role": "assistant", "content": full_content}
            if reasoning_content:
                assistant_message["reasoning_content"] = reasoning_content
            messages.append(assistant_message)

            # Display the tracked used files before the token usage summary.
            # Nothing is printed when no files were tracked (empty Text).
            used_files_report = format_used_files()
            if used_files_report:
                console.print(used_files_report, highlight=False)

            # Display token usage with magenta background
            if usage_info:
                total_tokens = getattr(usage_info, "total_tokens", None)
                input_tokens = getattr(usage_info, "input_tokens", None)
                output_tokens = getattr(usage_info, "output_tokens", None)

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
                parts.append(f"Messages: {len(messages)}")

                token_text = Text(f"=== {' | '.join(parts)} ===")
                token_text.stylize("white on magenta")
                console.print(token_text, highlight=False)
                logger.info(
                    f"Request completed: total={total_tokens} tokens "
                    f"(in={input_tokens}, out={output_tokens}, "
                    f"max={max_output_tokens}), {len(messages)} messages"
                )
            return full_content


__all__ = [
    "RequestCancelled",
    "send_prompt",
]
