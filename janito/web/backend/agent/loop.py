"""``stream_prompt()`` — the orchestration skeleton of the agentic loop.

Everything heavy lives in sibling modules; this generator reads top to
bottom: resolve config -> resolve tools -> loop { stream a response;
either run tool calls and continue, or finish }.
"""

import logging
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from janito.general_config import (
    get_active_provider,
    get_config_value,
    load_max_output_tokens,
    load_reasoning_level,
)
from janito.openai_client.client import resolve_runtime_config
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
from .call import StreamAccumulator, build_call_kwargs
from .tooling import reset_used_files, resolve_tools
from .turn import run_tool_turn

logger = logging.getLogger(__name__)


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
    # never written to disk — see WebServerConfig.session_provider.
    effective_provider = (
        config.session_provider or config.provider or get_active_provider()
    )
    try:
        base_url, api_key, model = resolve_runtime_config(
            cli_model=config.model, cli_provider=effective_provider
        )
    except Exception as e:
        yield ErrorEvent(message=str(e))
        return

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    if config.verbose:
        backend = base_url if base_url else "api.openai.com"
        logger.info(f"Web agent: model={model} backend={backend}")

    mcp_enabled = use_mcp
    tools_schemas = await resolve_tools(config, tools, use_mcp)

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

    messages.append({"role": "user", "content": prompt})

    first_turn = True
    while True:
        call_kwargs = build_call_kwargs(
            model, config, max_output_tokens, preserve_thinking, reasoning_level
        )
        call_kwargs["messages"] = messages
        if tools_schemas:
            call_kwargs["tools"] = tools_schemas
            call_kwargs["tool_choice"] = "auto"

        # Signal the browser that we're waiting for the API (replaces CLI spinner)
        yield WaitingEvent(phase="initial" if first_turn else "after_tools")
        first_turn = False

        # --- Stream the completion, yielding tokens as they arrive ---
        acc = StreamAccumulator()
        try:
            stream = await client.chat.completions.create(**call_kwargs)
            async for chunk in stream:
                reasoning_delta, content_delta = acc.handle(chunk)
                if reasoning_delta:
                    yield ReasoningEvent(content=reasoning_delta)
                if content_delta:
                    yield TokenEvent(content=content_delta)
        except Exception as e:
            logger.error(f"API streaming error: {e}")
            yield ErrorEvent(message=f"API error: {e!s}")
            return

        full_content = acc.full_content()

        # --- Handle tool calls -> continue the loop for the final response ---
        if acc.tool_calls:
            async for ev in run_tool_turn(
                acc.tool_calls_list(), full_content, messages, mcp_enabled
            ):
                yield ev
            continue

        # --- No tool calls: final response ---
        assistant_message = {"role": "assistant", "content": full_content}
        reasoning_content = acc.reasoning_content()
        if reasoning_content:
            assistant_message["reasoning_content"] = reasoning_content
        messages.append(assistant_message)

        usage_event = acc.usage_event(max_tokens=max_output_tokens)
        if usage_event:
            yield usage_event

        yield DoneEvent(full_content=full_content, message_count=len(messages))
        return
