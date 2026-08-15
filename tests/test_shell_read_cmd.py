"""
Tests for the /read shell command.

``/read <question>`` sends the prompt to the LLM using the **main**
conversation history (unlike ``/ask``, which starts a fresh history) but with
``tools=`` filtered down to the read-only (``"r"`` permission) tools. These
tests verify the command is registered, dispatches correctly, builds the
read-only tool schema list, and routes the prompt through the shell's
main-prompt path.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from janito.shell import InteractiveShell
from janito.shell.cmds.read import ReadCmdHandler, get_read_only_tool_schemas

# A fake tool schema pair: one read-only tool and one write tool.
READ_SCHEMA = {
    "type": "function",
    "function": {
        "name": "ReadFile",
        "description": "Read a file",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}
WRITE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "CreateFile",
        "description": "Create a file",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}


def _shell():
    """Build a fresh shell for testing."""
    return InteractiveShell(model="test-model", no_history=True)


# ---------------------------------------------------------------------------
# Registry / dispatch
# ---------------------------------------------------------------------------


def test_read_command_is_registered():
    from janito.shell.cmds import get_registered_commands

    names = [c.name for c in get_registered_commands()]
    assert "/read" in names


def test_handler_name():
    assert ReadCmdHandler().name == "/read"


def test_handle_dispatches_only_read_command(monkeypatch):
    handler = ReadCmdHandler()
    shell = _shell()
    shell.send_prompt_func = lambda **kw: None
    sent = {}

    def fake_send_prompt(prompt, tools=None):
        sent["prompt"] = prompt
        sent["tools"] = tools

    monkeypatch.setattr(shell, "_send_prompt", fake_send_prompt)
    monkeypatch.setattr(
        "janito.shell.cmds.read.get_read_only_tool_schemas",
        lambda: [READ_SCHEMA],
    )

    assert handler.handle(shell, "/read what is this?") is True
    assert sent["prompt"] == "what is this?"
    assert sent["tools"] == [READ_SCHEMA]

    # Case-insensitive command, question preserved.
    assert handler.handle(shell, "/READ tell me more") is True
    assert sent["prompt"] == "tell me more"

    # Bare '/read' matches but shows usage (no send).
    assert handler.handle(shell, "/read") is True

    # Non-matching inputs are not handled.
    assert handler.handle(shell, "/reads") is False
    assert handler.handle(shell, "/readme") is False
    assert handler.handle(shell, "/tools") is False
    assert handler.handle(shell, "hello") is False


def test_read_without_question_shows_usage(monkeypatch, capfd):
    handler = ReadCmdHandler()
    shell = _shell()
    called = {"n": 0}

    def fake_send_prompt(prompt, tools=None):
        called["n"] += 1

    monkeypatch.setattr(shell, "_send_prompt", fake_send_prompt)

    assert handler.handle(shell, "/read") is True
    out = capfd.readouterr().out
    assert "Usage: /read <your question>" in out
    assert "read-only tools" in out
    assert called["n"] == 0


def test_read_requires_send_prompt_func(monkeypatch, capfd):
    """Without send_prompt_func an error is printed instead of crashing."""
    handler = ReadCmdHandler()
    shell = _shell()
    # The shell has no send_prompt_func until run() sets it.
    assert handler.handle(shell, "/read hello") is True
    out = capfd.readouterr().out
    assert "No prompt function available" in out


# ---------------------------------------------------------------------------
# Read-only schema filtering
# ---------------------------------------------------------------------------


def test_get_read_only_tool_schemas_filters_by_r_permission(monkeypatch):
    """Only tools whose permissions are exactly ``"r"`` are included."""
    permissions = {
        "ReadFile": "r",
        "ListFiles": "r",
        "CreateFile": "w",
        "MoveFile": "rw",
        "RunBashCode": "x",
        "LoadSkill": "",  # skill tools declare no permissions
    }
    schemas = [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": f"Tool {name}",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }
        for name in permissions
    ]

    monkeypatch.setattr(
        "janito.tooling.tools_registry.get_all_tool_permissions",
        lambda: permissions,
    )
    monkeypatch.setattr(
        "janito.tooling.tools_registry.get_all_tool_schemas", lambda: schemas
    )

    result = get_read_only_tool_schemas()
    names = [s["function"]["name"] for s in result]
    assert names == ["ReadFile", "ListFiles"]
    assert "CreateFile" not in names
    assert "MoveFile" not in names
    assert "RunBashCode" not in names
    assert "LoadSkill" not in names


def test_get_read_only_tool_schemas_empty_without_r_tools(monkeypatch):
    """No read-only tools -> an empty list (equivalent to tools=[])."""
    monkeypatch.setattr(
        "janito.tooling.tools_registry.get_all_tool_permissions",
        lambda: {"CreateFile": "w", "RunBashCode": "x"},
    )
    monkeypatch.setattr(
        "janito.tooling.tools_registry.get_all_tool_schemas", lambda: [WRITE_SCHEMA]
    )

    assert get_read_only_tool_schemas() == []


# ---------------------------------------------------------------------------
# End-to-end routing through the main conversation
# ---------------------------------------------------------------------------


def test_read_routes_through_main_history_with_read_only_tools(monkeypatch):
    """/read goes through _send_prompt, which uses the main history and the
    filtered tools."""
    handler = ReadCmdHandler()
    shell = _shell()
    shell.initialize_history(system_prompt="sys")
    shell.verbose = False
    shell.thinking = False
    shell.no_tools = False

    monkeypatch.setattr(
        "janito.shell.cmds.read.get_read_only_tool_schemas",
        lambda: [READ_SCHEMA],
    )

    kwargs = {}

    def capture(prompt, **kw):
        kwargs["prompt"] = prompt
        kwargs.update(kw)
        return "assistant"

    shell.send_prompt_func = capture

    handler.handle(shell, "/read summarize the project")

    # The main history is used (mutated in place by the Completions client),
    # and only the read-only schemas are passed as tools.
    assert kwargs["prompt"] == "summarize the project"
    assert kwargs["previous_messages"] is shell.messages_history
    assert kwargs["instructions"] == "sys"
    assert kwargs["tools"] == [READ_SCHEMA]


if __name__ == "__main__":  # pragma: no cover
    if pytest is not None:
        raise SystemExit(pytest.main([__file__, "-v"]))
