"""Headless streaming agentic loop for the web backend.

This module lifts the agentic while-loop from
``janito/openai_client/client.py -> send_prompt()`` into an async generator
that yields structured events instead of printing to a terminal.

Reuses (unchanged) existing janito modules:
  - ``janito.openai_client.client.get_env_config()``  -> config resolution
  - ``janito.tooling.tools_registry.*``                -> schemas + lookup
  - ``janito.mcp_manager.get_mcp_manager()``           -> MCP tools
  - ``janito.general_config.*``                        -> context window, etc.

No Rich imports anywhere. Uses ``openai.AsyncOpenAI`` for non-blocking I/O.
"""

import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Dict, List, Optional

from openai import AsyncOpenAI

from janito.openai_client.client import get_env_config, format_tokens
from janito.general_config import (
    load_context_window_size,
    get_config_value,
    get_active_provider,
)

from .config import WebServerConfig
from .events import (
    AgentEvent, TokenEvent, ReasoningEvent, ToolCallEvent, ToolResultEvent,
    ToolProgressEvent, WaitingEvent, UsageEvent, DoneEvent, ErrorEvent,
)

logger = logging.getLogger(__name__)

# Import tools registry (lazy-safe — mirrors client.py behaviour)
try:
    from janito.tooling.tools_registry import (
        get_all_tool_schemas, get_tool_by_name, get_tool_permissions,
    )
    TOOLS_AVAILABLE = True
except (ImportError, ValueError):
    TOOLS_AVAILABLE = False

    def get_all_tool_schemas():
        return []

    def get_tool_by_name(name):
        raise NotImplementedError("Tools not available")

    def get_tool_permissions(name):
        return ""

# Import MCP manager
try:
    from janito.mcp_manager import get_mcp_manager
    MCP_MANAGER_AVAILABLE = True
except ImportError:
    MCP_MANAGER_AVAILABLE = False

    def get_mcp_manager():
        return None

# Reporter handler for capturing tool output in web mode
from janito.tooling.reporter import set_report_handler


def _is_mcp_tool(tool_name: str) -> bool:
    """Check if a tool name is an MCP tool (has service_ prefix)."""
    mcp_manager = get_mcp_manager()
    if mcp_manager:
        return mcp_manager.get_service_for_tool(tool_name) is not None
    return False


async def _execute_tool(tool_call_id: str, tool_name: str, tool_args: dict,
                        use_mcp: bool):
    """Execute a single tool call, capturing report_* output as progress events.

    Returns a tuple ``(result_dict, progress_events, error, exec_time_ms)``.
    The tool runs in a thread (tools are synchronous); ``contextvars`` ensure
    the report handler is visible inside the thread and isolated per-task.
    """
    progress_events: List[ToolProgressEvent] = []

    def handler(level: str, message: str, end: str):
        progress_events.append(ToolProgressEvent(
            tool_call_id=tool_call_id,
            level=level,
            message=message,
        ))

    start = time.time()
    set_report_handler(handler)
    error: Optional[str] = None
    result = None
    try:
        if use_mcp and _is_mcp_tool(tool_name):
            mcp_manager = get_mcp_manager()
            result = await asyncio.to_thread(
                mcp_manager.call_tool, tool_name, tool_args
            )
        else:
            tool_fn = get_tool_by_name(tool_name)
            result = await asyncio.to_thread(tool_fn, **tool_args)
    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        error = str(e)
        result = {
            "success": False,
            "error": f"Tool execution failed: {str(e)}",
        }
    finally:
        set_report_handler(None)  # restore default (Rich console)

    exec_time_ms = int((time.time() - start) * 1000)
    return result, progress_events, error, exec_time_ms


async def stream_prompt(
    prompt: str,
    messages: List[dict],
    config: WebServerConfig,
    tools: Optional[List[dict]] = None,
    use_mcp: bool = True,
) -> AsyncGenerator[AgentEvent, None]:
    """Yield structured events instead of printing to terminal.

    Config-driven behaviour (from CLI args):
      - ``config.no_tools``  -> pass empty tools list
      - ``config.thinking``  -> add extra_body enable_thinking
      - ``config.verbose``   -> log model/backend info

    Args:
        prompt: The user prompt to send.
        messages: Caller-owned conversation history (mutated in place).
        config: Runtime config from CLI args.
        tools: Optional explicit tool schemas. ``None`` = auto-discover
               (unless ``config.no_tools``).
        use_mcp: If True, load and use MCP tools.
    """
    try:
        base_url, api_key, model = get_env_config()
    except Exception as e:
        yield ErrorEvent(message=str(e))
        return

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    if config.verbose:
        backend = base_url if base_url else "api.openai.com"
        logger.info(f"Web agent: model={model} backend={backend}")

    # --- Resolve tools ---
    mcp_manager = None
    if not config.no_tools:
        if use_mcp and MCP_MANAGER_AVAILABLE:
            mcp_manager = get_mcp_manager()
            try:
                await asyncio.to_thread(mcp_manager.load_services)
                mcp_tools = await asyncio.to_thread(mcp_manager.get_all_tools)
                logger.info(
                    f"Loaded {len(mcp_tools)} MCP tools from "
                    f"{len(mcp_manager.connected_services)} services"
                )
            except Exception as e:
                logger.warning(f"Failed to load MCP tools: {e}")
                mcp_tools = []
        else:
            mcp_tools = []

        if tools is None:
            built_in_tools = get_all_tool_schemas() if TOOLS_AVAILABLE else []
            tools_schemas = built_in_tools + mcp_tools
        else:
            tools_schemas = tools
    else:
        tools_schemas = []
        mcp_tools = []

    context_window_size = load_context_window_size(get_active_provider())
    preserve_thinking = get_config_value("preserve_thinking")

    messages.append({"role": "user", "content": prompt})

    first_turn = True
    while True:
        # Build the base call parameters
        call_kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 1.0,
        }

        if context_window_size is not None:
            if model.startswith("gpt-5"):
                call_kwargs["max_completion_tokens"] = context_window_size
            else:
                call_kwargs["max_tokens"] = context_window_size

        if preserve_thinking is not None:
            call_kwargs.setdefault("extra_body", {})["preserve_thinking"] = preserve_thinking

        if config.thinking:
            call_kwargs.setdefault("extra_body", {})["enable_thinking"] = True

        call_kwargs["stream"] = True
        call_kwargs["stream_options"] = {"include_usage": True}

        # Signal the browser that we're waiting for the API (replaces CLI spinner)
        yield WaitingEvent(phase="initial" if first_turn else "after_tools")
        first_turn = False

        # --- Stream the completion, yielding tokens as they arrive ---
        collected_content: List[str] = []
        collected_reasoning: List[str] = []
        tool_calls_map: Dict[int, Dict[str, str]] = {}
        usage_info = None

        try:
            if tools_schemas:
                stream = await client.chat.completions.create(
                    **call_kwargs, tools=tools_schemas, tool_choice="auto",
                )
            else:
                stream = await client.chat.completions.create(**call_kwargs)

            async for chunk in stream:
                if hasattr(chunk, "usage") and chunk.usage:
                    usage_info = chunk.usage

                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                # Reasoning / thinking content
                reasoning_chunk = None
                for attr in ("reasoning_content", "reasoning"):
                    val = getattr(delta, attr, None)
                    if val:
                        reasoning_chunk = val
                        collected_reasoning.append(val)
                        break
                if reasoning_chunk:
                    yield ReasoningEvent(content=reasoning_chunk)

                # Main content
                if delta.content:
                    collected_content.append(delta.content)
                    yield TokenEvent(content=delta.content)

                # Tool-call deltas (split across many chunks)
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
        except Exception as e:
            logger.error(f"API streaming error: {e}")
            yield ErrorEvent(message=f"API error: {str(e)}")
            return

        full_content = "".join(collected_content)
        reasoning_content = "".join(collected_reasoning) if collected_reasoning else None

        # --- Handle tool calls ---
        if tool_calls_map:
            tool_calls_list = []
            for idx in sorted(tool_calls_map):
                tc = tool_calls_map[idx]
                tool_calls_list.append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"],
                    },
                })
            assistant_msg: Dict = {
                "role": "assistant",
                "content": full_content or None,
                "tool_calls": tool_calls_list,
            }
            messages.append(assistant_msg)

            for tc in tool_calls_list:
                tool_name = tc["function"]["name"]
                try:
                    tool_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    tool_args = {}
                tool_call_id = tc["id"]

                logger.info(f"Web tool call: {tool_name}({tool_args})")

                permissions = ""
                if not _is_mcp_tool(tool_name):
                    try:
                        permissions = get_tool_permissions(tool_name)
                    except Exception:
                        permissions = ""

                yield ToolCallEvent(
                    tool_call_id=tool_call_id,
                    tool_name=tool_name,
                    arguments=tool_args,
                    permissions=permissions,
                )

                result, progress_events, error, exec_ms = await _execute_tool(
                    tool_call_id, tool_name, tool_args, use_mcp and MCP_MANAGER_AVAILABLE
                )

                # Yield captured progress events (report_* output)
                for pe in progress_events:
                    yield pe

                yield ToolResultEvent(
                    tool_call_id=tool_call_id,
                    tool_name=tool_name,
                    result=result,
                    error=error,
                    execution_time_ms=exec_ms,
                )

                messages.append({
                    "tool_call_id": tool_call_id,
                    "role": "tool",
                    "name": tool_name,
                    "content": json.dumps(result) if not isinstance(result, str) else result,
                })

            # Continue the loop to get the final response after tool calls
            continue

        # --- No tool calls: final response ---
        assistant_message = {"role": "assistant", "content": full_content}
        if reasoning_content:
            assistant_message["reasoning_content"] = reasoning_content
        messages.append(assistant_message)

        if usage_info:
            yield UsageEvent(
                total=getattr(usage_info, "total_tokens", 0) or 0,
                input=getattr(usage_info, "prompt_tokens", 0) or 0,
                output=getattr(usage_info, "completion_tokens", 0) or 0,
                cached=(
                    getattr(getattr(usage_info, "prompt_tokens_details", None),
                            "cached_tokens", 0) or 0
                ),
            )

        yield DoneEvent(full_content=full_content, message_count=len(messages))
        return
