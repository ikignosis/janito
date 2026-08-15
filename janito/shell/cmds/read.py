"""
/read command handler - sends a prompt to the LLM using the main conversation
history but restricted to read-only tools.

Unlike ``/ask`` (which starts a fresh, isolated chat history), ``/read`` sends
the prompt through the main conversation: the model sees the ongoing history
and the exchange is appended to it (rollback/cancel behaviour matches a normal
prompt). The only difference is that ``tools=`` is filtered down to the
read-only tools -- the built-in tools whose ``@tool(permissions="r")``
declares read access and nothing else, so the model can inspect, search and
fetch but cannot write or execute.
"""

from .base import CmdHandler
from .registry import register_command


def get_read_only_tool_schemas() -> list[dict]:
    """Return the function-calling schemas of the read-only (``"r"``) tools.

    A tool is considered read-only when its ``_tool_permissions`` is exactly
    ``"r"`` (the value set by ``@tool(permissions="r")``): read access and
    nothing else. Tools declaring no permissions (e.g. the skill tools) and
    tools that can write or execute (``"w"``/``"x"``/combinations) are
    excluded. MCP tools carry no permission metadata here, so they are
    excluded too -- only the built-in read-only tools are offered.
    """
    from janito.tooling.tools_registry import (
        get_all_tool_permissions,
        get_all_tool_schemas,
    )

    read_only_names = {
        name
        for name, permissions in get_all_tool_permissions().items()
        if permissions == "r"
    }
    return [
        schema
        for schema in get_all_tool_schemas()
        if schema.get("function", {}).get("name") in read_only_names
    ]


class ReadCmdHandler(CmdHandler):
    """Command handler for /read - asks the LLM with read-only tools."""

    @property
    def name(self) -> str:
        return "/read"

    def handle(self, shell, user_input: str) -> bool:
        """Handle the /read command."""
        # Match '/read' exactly or '/read <question>' (not '/reads', etc.)
        if (
            user_input.lower() != self.name.lower()
            and not user_input.lower().startswith(self.name.lower() + " ")
        ):
            return False

        # Extract the question (everything after '/read ')
        question = user_input[len(self.name) :].strip()

        if not question:
            print("\nUsage: /read <your question>")
            print(
                "  Sends the prompt to the LLM using the main conversation"
                " history, but restricted to read-only tools."
            )
            print(
                "  The exchange stays in the main conversation history"
                " (rollback/cancel behave like a normal prompt).\n"
            )
            return True

        self._read(shell, question)
        return True

    def _read(self, shell, question: str) -> None:
        """Send the prompt with the main history, using only read-only tools."""
        send_prompt_func = getattr(shell, "send_prompt_func", None)
        if send_prompt_func is None:
            print(
                "\nError: No prompt function available. Are you in an active session?\n"
            )
            return

        read_only_schemas = get_read_only_tool_schemas()
        print()  # blank line before the streamed response, like /ask
        # Reuse the shell's main-prompt path: same history, checkpoints,
        # Responses state sync and cancel/rollback handling -- only the tool
        # set is restricted to the read-only tools.
        shell._send_prompt(question, tools=read_only_schemas)


# Register this handler
_handler = ReadCmdHandler()
register_command(_handler)
