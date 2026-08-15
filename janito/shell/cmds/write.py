"""
/write command handler - sends a prompt to the LLM using the main conversation
history but restricted to write-only tools.

Unlike ``/ask`` (which starts a fresh, isolated chat history), ``/write`` sends
the prompt through the main conversation: the model sees the ongoing history
and the exchange is appended to it (rollback/cancel behaviour matches a normal
prompt). The only difference is that ``tools=`` is filtered down to the
write-only tools -- the built-in tools whose ``@tool(permissions="w")``
declares write access and nothing else, so the model can create, modify or
delete but cannot read, search or execute.
"""

from ._tool_filters import get_tool_schemas_by_permission
from .base import CmdHandler
from .registry import register_command


def get_write_only_tool_schemas() -> list[dict]:
    """Return the function-calling schemas of the write-only (``"w"``) tools.

    A tool is considered write-only when its ``_tool_permissions`` is exactly
    ``"w"`` (the value set by ``@tool(permissions="w")``): write access and
    nothing else. Tools declaring no permissions (e.g. the skill tools) and
    tools that can also read or execute (``"r"``/``"x"``/combinations) are
    excluded. MCP tools carry no permission metadata here, so they are
    excluded too -- only the built-in write-only tools are offered.
    """
    return get_tool_schemas_by_permission("w")


class WriteCmdHandler(CmdHandler):
    """Command handler for /write - asks the LLM with write-only tools."""

    @property
    def name(self) -> str:
        return "/write"

    def handle(self, shell, user_input: str) -> bool:
        """Handle the /write command."""
        # Match '/write' exactly or '/write <question>' (not '/writes', etc.)
        if (
            user_input.lower() != self.name.lower()
            and not user_input.lower().startswith(self.name.lower() + " ")
        ):
            return False

        # Extract the question (everything after '/write ')
        question = user_input[len(self.name) :].strip()

        if not question:
            print("\nUsage: /write <your question>")
            print(
                "  Sends the prompt to the LLM using the main conversation"
                " history, but restricted to write-only tools."
            )
            print(
                "  The exchange stays in the main conversation history"
                " (rollback/cancel behave like a normal prompt).\n"
            )
            return True

        self._write(shell, question)
        return True

    def _write(self, shell, question: str) -> None:
        """Send the prompt with the main history, using only write-only tools."""
        send_prompt_func = getattr(shell, "send_prompt_func", None)
        if send_prompt_func is None:
            print(
                "\nError: No prompt function available. Are you in an active session?\n"
            )
            return

        write_only_schemas = get_write_only_tool_schemas()
        print()  # blank line before the streamed response, like /ask
        # Reuse the shell's main-prompt path: same history, checkpoints,
        # Responses state sync and cancel/rollback handling -- only the tool
        # set is restricted to the write-only tools.
        shell._send_prompt(question, tools=write_only_schemas)


# Register this handler
_handler = WriteCmdHandler()
register_command(_handler)
