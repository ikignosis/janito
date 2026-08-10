"""Headless streaming agentic loop for the web backend.

This package lifts the agentic while-loop from
``janito/openai_client/completions_api.py -> send_prompt()`` into an async generator
that yields structured events instead of printing to a terminal.  It is the
**web orchestration loop**; the per-API adapters it dispatches to (call-kwargs
building, stream accumulation, history conversion) live in the shared
``janito.agent`` layer, also used by the CLI ``Client.send`` loop.  The
runner modules here are thin shims that re-export the shared adapters and
keep the web-only async glue (SDK client creation + event-stream drivers).

Modules:
  - :mod:`~.tooling` — tool discovery (built-in + MCP) and execution.
  - :mod:`~.call`    — Completions adapter (shared) re-export.
  - :mod:`~.responses`  — Responses API runner (input-items conversation model).
  - :mod:`~.anthropic`  — native Anthropic SDK runner (system/tool conversion).
  - :mod:`~.dashscope`  — native DashScope SDK runner (off-thread stream).
  - :mod:`~.turn`    — the tool-call leg of one agentic turn (as events).
  - :mod:`~.loop`    — ``stream_prompt()``, the orchestration skeleton that
                  dispatches to the API type selected for the provider.

Reuses (unchanged) existing janito modules:
  - ``janito.openai_client.completions_api.resolve_runtime_config()`` -> config resolution
  - ``janito.tooling.tools_registry.*``               -> schemas + lookup
  - ``janito.tooling.executor.run_tool``              -> shared tool-execution core
  - ``janito.mcp_manager.get_mcp_manager()``          -> MCP tools
  - ``janito.general_config.*``                       -> context window, etc.

No Rich imports anywhere. Uses ``openai.AsyncOpenAI`` for non-blocking I/O
(plus the native ``anthropic``/``dashscope`` SDKs for those API types).
"""

from .loop import stream_prompt

__all__ = ["stream_prompt"]
