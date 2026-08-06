"""Headless streaming agentic loop for the web backend.

This package lifts the agentic while-loop from
``janito/openai_client/completions_api.py -> send_prompt()`` into an async generator
that yields structured events instead of printing to a terminal.

Modules:
  - :mod:`~.tooling` — tool discovery (built-in + MCP) and execution.
  - :mod:`~.call`    — OpenAI call-parameter building + stream accumulation.
  - :mod:`~.turn`    — the tool-call leg of one agentic turn (as events).
  - :mod:`~.loop`    — ``stream_prompt()``, the orchestration skeleton.

Reuses (unchanged) existing janito modules:
  - ``janito.openai_client.completions_api.resolve_runtime_config()`` -> config resolution
  - ``janito.tooling.tools_registry.*``               -> schemas + lookup
  - ``janito.mcp_manager.get_mcp_manager()``          -> MCP tools
  - ``janito.general_config.*``                       -> context window, etc.

No Rich imports anywhere. Uses ``openai.AsyncOpenAI`` for non-blocking I/O.
"""

from .loop import stream_prompt

__all__ = ["stream_prompt"]
