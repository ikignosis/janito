"""``stream_prompt()`` — the orchestration skeleton of the agentic loop.

Everything heavy lives in sibling modules; this generator reads top to
bottom: resolve config -> resolve API type -> resolve tools -> loop { stream a
response; either run tool calls and continue, or finish }.

The loop is API-type agnostic.  The API type for the turn is resolved for the
*effective provider* (the one selected for the session/provider combo) via
``resolve_api_type`` — ``--api-type`` first, then the provider's configured
``api-type`` (written by the web Settings drawer), then the provider's
built-in default.  Each API type contributes a small runner (client factory,
call-kwargs builder, accumulator, stream driver) exposing the same interface:

- Completions  -> ``janito.web.backend.agent.call`` (this module's built-in)
- Responses    -> ``janito.web.backend.agent.responses``
- Anthropic    -> ``janito.web.backend.agent.anthropic``
- DashScope    -> ``janito.web.backend.agent.dashscope``
"""

import logging
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from janito.general_config import (
    get_active_provider,
    get_config_value,
    load_max_output_tokens,
    load_reasoning_level,
    resolve_api_type,
)
from janito.openai_client.completions_api import resolve_runtime_config
from janito.provider_config import (
    get_default_max_output_tokens_from_provider,
    get_default_reasoning_level_from_provider,
)

from ..config import WebServerConfig
from ..events import (
    AgentEvent,
    DoneEvent,
    ErrorEvent,
    ReasoningEvent,
    TokenEvent,
    WaitingEvent,
)
from . import anthropic as anthropic_runner
from . import dashscope as dashscope_runner
from . import responses as responses_runner
from .call import StreamAccumulator, build_call_kwargs
from .tooling import reset_used_files, resolve_tools
from .turn import run_tool_turn

logger = logging.getLogger(__name__)


def _resolve_turn_config(config, effective_provider):
    """Resolve max tokens / preserve_thinking / reasoning level for the turn."""
    max_output_tokens = load_max_output_tokens(effective_provider)
    if max_output_tokens is None:
        # Fall back to the provider's built-in default (PROVIDER_INFO).
        max_output_tokens = get_default_max_output_tokens_from_provider(
            effective_provider
        )
    preserve_thinking = get_config_value("preserve_thinking")

    # Reasoning level (reasoning_effort): per-provider config value first,
    # then the provider's built-in default (e.g. "xhigh" for qwen3.8-max).
    reasoning_level = load_reasoning_level(effective_provider)
    if reasoning_level is None:
        reasoning_level = get_default_reasoning_level_from_provider(effective_provider)

    return max_output_tokens, preserve_thinking, reasoning_level


def _runner_for(api_type: str):
    """Return the web-agent runner module for a non-Completions API type.

    ``None`` means the built-in Completions path (``call.py``) applies.
    """
    if api_type == "Responses":
        return responses_runner
    if api_type == "Anthropic":
        return anthropic_runner
    if api_type == "DashScope":
        return dashscope_runner
    return None


def _build_turn_kwargs(
    model,
    config,
    tools_schemas,
    messages,
    max_output_tokens,
    preserve_thinking,
    reasoning_level,
) -> dict:
    """Build the ``chat.completions.create`` kwargs for one turn."""
    call_kwargs = build_call_kwargs(
        model,
        config,
        max_output_tokens,
        preserve_thinking,
        reasoning_level,
    )
    call_kwargs["messages"] = messages
    if tools_schemas:
        call_kwargs["tools"] = tools_schemas
        call_kwargs["tool_choice"] = "auto"
    return call_kwargs


def _build_assistant_message(acc: StreamAccumulator, full_content: str) -> dict:
    """Build the assistant message dict from the accumulated turn."""
    assistant_message = {"role": "assistant", "content": full_content}
    reasoning_content = acc.reasoning_content()
    if reasoning_content:
        assistant_message["reasoning_content"] = reasoning_content
    # Native Responses-API image generation (image_generation tool): attach
    # the saved image paths so the frontend can rebuild the content cards
    # when the session history is reloaded.  Completions runners never set
    # ``image_results``, so getattr keeps this a no-op for them.
    image_results = getattr(acc, "image_results", None) or []
    if image_results:
        assistant_message["images"] = [
            {"path": img["path"], "revised_prompt": img.get("revised_prompt", "")}
            for img in image_results
        ]
    return assistant_message


def _create_agent_client(runner, base_url, api_key):
    """Create the SDK client for the API type (Completions is built-in)."""
    if runner is None:
        return AsyncOpenAI(api_key=api_key, base_url=base_url)
    return runner.create_client(base_url, api_key)


def _turn_call_kwargs_and_acc(
    runner,
    model,
    config,
    tools_schemas,
    messages,
    max_output_tokens,
    preserve_thinking,
    reasoning_level,
):
    """Build the per-type call kwargs and a fresh accumulator for one turn."""
    if runner is None:
        call_kwargs = _build_turn_kwargs(
            model,
            config,
            tools_schemas,
            messages,
            max_output_tokens,
            preserve_thinking,
            reasoning_level,
        )
        return call_kwargs, StreamAccumulator()
    call_kwargs = runner.build_call_kwargs(
        model,
        messages,
        tools_schemas,
        config,
        max_output_tokens,
        preserve_thinking,
        reasoning_level,
    )
    return call_kwargs, runner.accumulator()


async def _stream_turn(client, runner, call_kwargs, acc):
    """Stream one API turn, yielding reasoning/token events.

    The caller owns ``acc``; on completion it holds the full turn state for
    end-of-turn assembly.
    """
    if runner is None:
        stream = await client.chat.completions.create(**call_kwargs)
        async for chunk in stream:
            reasoning_delta, content_delta = acc.handle(chunk)
            if reasoning_delta:
                yield ReasoningEvent(content=reasoning_delta)
            if content_delta:
                yield TokenEvent(content=content_delta)
        return
    async for ev in runner.stream_turn_events(client, call_kwargs, acc):
        yield ev


async def stream_prompt(
    prompt: str,
    messages: list[dict],
    config: WebServerConfig,
    tools: list[dict] | None = None,
    use_mcp: bool = True,
) -> AsyncGenerator[AgentEvent, None]:
    """Yield structured events instead of printing to terminal.

    Args:
        prompt: The user prompt to send.
        messages: Caller-owned conversation history (mutated in place).
        config: Runtime config from CLI args.
        tools: Optional explicit tool schemas. ``None`` = auto-discover
               (unless ``config.no_tools``).
        use_mcp: If True, load and use MCP tools.
    """
    # Clear the in-process used-files tracker so per-prompt tracking only
    # reflects the files touched while handling the *current* prompt (best
    # effort, never raises), mirroring the CLI's ``send_prompt`` behaviour.
    reset_used_files()
    # Effective provider for this turn: a session-only override picked from
    # the chat-page combo wins over the CLI --provider, which wins over the
    # persisted default (config.json / auth.json).  The session override is
    # never written to disk -- see WebServerConfig.session_provider.
    effective_provider = (
        config.session_provider or config.provider or get_active_provider()
    )
    # The API type for this turn: --api-type first, then the provider's
    # configured api-type (the web Settings drawer's per-provider combo, the
    # same value the CLI's --set api-type=... writes), then the provider's
    # built-in default (the first of its supported_api_types).
    api_type = resolve_api_type(config.api_type, effective_provider)
    runner = _runner_for(api_type)

    try:
        # Endpoint resolution honors the API type: providers with an
        # ``endpoint_by_api_type`` map get their per-type base URL (e.g.
        # DeepSeek's Anthropic-compatible URL, Alibaba's native-SDK URL).
        base_url, api_key, model = resolve_runtime_config(
            cli_model=config.model,
            cli_provider=effective_provider,
            cli_api_type=api_type,
        )
    except Exception as e:
        yield ErrorEvent(message=str(e))
        return

    try:
        client = _create_agent_client(runner, base_url, api_key)
    except Exception as e:
        yield ErrorEvent(message=str(e))
        return

    if config.verbose:
        backend = base_url if base_url else "api.openai.com"
        logger.info(f"Web agent: model={model} backend={backend} api_type={api_type}")

    mcp_enabled = use_mcp
    tools_schemas = await resolve_tools(config, tools, use_mcp)

    max_output_tokens, preserve_thinking, reasoning_level = _resolve_turn_config(
        config, effective_provider
    )

    messages.append({"role": "user", "content": prompt})

    first_turn = True
    while True:
        call_kwargs, acc = _turn_call_kwargs_and_acc(
            runner,
            model,
            config,
            tools_schemas,
            messages,
            max_output_tokens,
            preserve_thinking,
            reasoning_level,
        )

        # Signal the browser that we're waiting for the API (replaces CLI spinner)
        yield WaitingEvent(phase="initial" if first_turn else "after_tools")
        first_turn = False

        # --- Stream the completion, yielding tokens as they arrive ---
        try:
            async for ev in _stream_turn(client, runner, call_kwargs, acc):
                yield ev
        except Exception as e:
            logger.error(f"API streaming error: {e}")
            yield ErrorEvent(message=f"API error: {e!s}")
            return

        full_content = acc.full_content()

        # --- Handle tool calls -> continue the loop for the final response ---
        if acc.tool_calls_list():
            async for ev in run_tool_turn(
                acc.tool_calls_list(), full_content, messages, mcp_enabled
            ):
                yield ev
            continue

        # --- No tool calls: final response ---
        messages.append(_build_assistant_message(acc, full_content))

        usage_event = acc.usage_event(max_tokens=max_output_tokens)
        if usage_event:
            yield usage_event

        yield DoneEvent(full_content=full_content, message_count=len(messages))
        return
