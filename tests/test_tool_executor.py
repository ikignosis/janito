"""
Tests for the tool executor (:mod:`janito.tooling.executor`).

``ToolExecutor`` executes the tool calls the model produces during a turn: it
builds the assistant message carrying the calls, routes each call to the MCP
manager or the built-in tools registry, records tool usage / used files /
changes, and appends ``tool``-role responses to the conversation history. A
failing call is converted into a structured error result and never raises.

The executor uses the module-global tools registry, so tests register stub
tools there (mirroring :mod:`tests.test_used_files`) and point the config dir
at a temporary directory so usage/changes tracking stays hermetic.
"""

import json
import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.config_dir as config_dir_mod
import janito.tooling.executor as executor_mod
import janito.tooling.tools_registry as tools_registry
import janito.tooling.used_files as used_files
from janito.tooling.executor import ToolExecutor


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Run each test in a temp CWD with a temp config dir and clean state.

    The changes log (``./.janito/changes.jsonl``) and the usage database
    (``<config_dir>/tools_use.db``) both depend on process-global locations,
    so each test gets its own temp dirs and the in-memory used-files tracker
    is reset before and after.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config_dir_mod, "_config_dir", tmp_path)
    used_files.reset_used_files()
    yield
    used_files.reset_used_files()


def _register(monkeypatch, name, permissions, result=None):
    """Register a stub tool in the registry for the duration of a test.

    Sets ``_tools_initialized`` so the registry never triggers the (slow,
    filesystem-scanning) real discovery, and injects a stub callable carrying
    the ``_tool_permissions`` attribute the trackers read.
    """
    monkeypatch.setattr(tools_registry, "_tools_initialized", True)

    def fake(**kwargs):
        return result if result is not None else {"success": True}

    fake._tool_permissions = permissions
    monkeypatch.setitem(tools_registry.AVAILABLE_TOOLS, name, fake)


class _FakeMCPManager:
    """Minimal stand-in for MCPManager recording ``call_tool`` invocations."""

    def __init__(self):
        self.calls = []

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return {"success": True, "mcp": True}


def _tool_call(call_id, name, arguments="{}"):
    """Build a single OpenAI-style tool-call dict."""
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }


if pytest is not None:

    def test_build_assistant_message_sorts_by_index():
        """Calls are ordered by their stream index, not insertion order."""
        ex = ToolExecutor()
        msg = ex.build_assistant_message(
            "thinking",
            {
                1: {"id": "call_b", "name": "ToolB", "arguments": "{}"},
                0: {"id": "call_a", "name": "ToolA", "arguments": '{"x": 1}'},
            },
        )
        assert msg["role"] == "assistant"
        assert msg["content"] == "thinking"
        assert msg["tool_calls"] == [
            {
                "id": "call_a",
                "type": "function",
                "function": {"name": "ToolA", "arguments": '{"x": 1}'},
            },
            {
                "id": "call_b",
                "type": "function",
                "function": {"name": "ToolB", "arguments": "{}"},
            },
        ]

    def test_build_assistant_message_empty_content_becomes_none():
        """An empty assistant text is stored as ``None`` in the message."""
        ex = ToolExecutor()
        msg = ex.build_assistant_message(
            "", {0: {"id": "c", "name": "Tool", "arguments": "{}"}}
        )
        assert msg["content"] is None

    def test_build_assistant_message_preserves_extra_content():
        """Provider extras (Gemini thought_signature) are echoed back.

        Gemini 3.x rejects the follow-up request unless the replayed function
        call keeps the ``extra_content.google.thought_signature`` it was
        issued with, so the assistant message must carry it verbatim.
        """
        ex = ToolExecutor()
        extra = {"google": {"thought_signature": "SIG-12345"}}
        msg = ex.build_assistant_message(
            "",
            {
                0: {
                    "id": "call_1",
                    "name": "FindFiles",
                    "arguments": "{}",
                    "extra_content": extra,
                }
            },
        )
        assert msg["tool_calls"] == [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "FindFiles", "arguments": "{}"},
                "extra_content": extra,
            }
        ]

    def test_build_assistant_message_omits_extra_content_when_absent():
        """Calls without provider extras keep the plain OpenAI shape."""
        ex = ToolExecutor()
        msg = ex.build_assistant_message(
            "", {0: {"id": "call_1", "name": "FindFiles", "arguments": "{}"}}
        )
        assert msg["tool_calls"] == [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "FindFiles", "arguments": "{}"},
            }
        ]

    def test_execute_tool_call_runs_builtin_tool(monkeypatch):
        """A built-in call is routed to the registry and its result returned."""
        _register(monkeypatch, "MyTool", "r")
        ex = ToolExecutor()
        message = ex.execute_tool_call(
            _tool_call("call_1", "MyTool", '{"filepath": "a.txt"}')
        )
        assert message["tool_call_id"] == "call_1"
        assert message["role"] == "tool"
        assert message["name"] == "MyTool"
        assert json.loads(message["content"]) == {"success": True}

    def test_execute_tool_call_returns_structured_error(monkeypatch):
        """An unknown tool produces a structured error result, never raises."""
        _register(monkeypatch, "MyTool", "r")
        ex = ToolExecutor()
        message = ex.execute_tool_call(_tool_call("call_err", "NoSuchTool"))
        payload = json.loads(message["content"])
        assert payload["success"] is False
        assert "error" in payload
        assert message["name"] == "NoSuchTool"
        assert message["tool_call_id"] == "call_err"

    def test_execute_tool_call_propagates_keyboard_interrupt(monkeypatch):
        """Ctrl+C inside a tool (e.g. AskUser) must NOT be swallowed by the
        executor's error safety net: it propagates so the agent loop can be
        interrupted (history rolled back), instead of continuing with an
        empty answer."""
        _register(monkeypatch, "MyTool", "r")

        def fake(**kwargs):
            raise KeyboardInterrupt

        monkeypatch.setitem(tools_registry.AVAILABLE_TOOLS, "MyTool", fake)
        ex = ToolExecutor()

        with pytest.raises(KeyboardInterrupt):
            ex.execute_tool_call(_tool_call("call_1", "MyTool"))

    def test_execute_tool_call_records_usage(monkeypatch):
        """Every invocation is recorded by the usage tracker (best-effort)."""
        _register(monkeypatch, "MyTool", "r")
        recorded = []

        def fake_record(tool_name):
            recorded.append(tool_name)

        monkeypatch.setattr(executor_mod, "record_tool_use", fake_record)
        ex = ToolExecutor()
        ex.execute_tool_call(_tool_call("call_1", "MyTool"))
        assert recorded == ["MyTool"]

    def test_execute_tool_call_records_used_files_on_success(monkeypatch):
        """A successful file-touching call is tracked in used_files."""
        _register(monkeypatch, "MyTool", "rw")
        ex = ToolExecutor()
        ex.execute_tool_call(_tool_call("call_1", "MyTool", '{"filepath": "/a.py"}'))
        assert used_files.get_used_files() == {
            "READ": ["/a.py"],
            "WRITE": ["/a.py"],
        }

    def test_execute_tool_call_skips_tracking_on_logical_failure(monkeypatch):
        """A ``{"success": False}`` result is not tracked as a used file."""
        _register(monkeypatch, "MyTool", "rw", result={"success": False})
        ex = ToolExecutor()
        ex.execute_tool_call(_tool_call("call_1", "MyTool", '{"filepath": "/a.py"}'))
        assert used_files.get_used_files() == {"READ": [], "WRITE": []}

    def test_execute_tool_call_skips_tracking_on_exception(monkeypatch):
        """A raising tool is not tracked as a used file."""
        _register(monkeypatch, "MyTool", "rw")
        ex = ToolExecutor()
        ex.execute_tool_call(
            _tool_call("call_1", "NoSuchTool", '{"filepath": "/a.py"}')
        )
        assert used_files.get_used_files() == {"READ": [], "WRITE": []}

    def test_execute_tool_call_routes_to_mcp_manager(monkeypatch):
        """MCP tools are routed to the manager's ``call_tool``."""
        manager = _FakeMCPManager()
        monkeypatch.setattr(executor_mod, "is_mcp_tool", lambda name: True)
        ex = ToolExecutor(mcp_manager=manager)
        message = ex.execute_tool_call(_tool_call("mcp_1", "svc_read", '{"path": "x"}'))
        assert manager.calls == [("svc_read", {"path": "x"})]
        assert json.loads(message["content"]) == {"success": True, "mcp": True}

    def test_execute_tool_call_uses_registry_for_non_mcp(monkeypatch):
        """Non-MCP tools go to the registry even when a manager is bound."""
        manager = _FakeMCPManager()
        _register(monkeypatch, "MyTool", "r")
        monkeypatch.setattr(executor_mod, "is_mcp_tool", lambda name: False)
        ex = ToolExecutor(mcp_manager=manager)
        message = ex.execute_tool_call(_tool_call("call_1", "MyTool"))
        assert manager.calls == []
        assert json.loads(message["content"]) == {"success": True}

    def test_execute_tool_calls_appends_one_message_per_call(monkeypatch):
        """``execute_tool_calls`` appends a tool message for every call."""
        _register(monkeypatch, "MyTool", "r")
        ex = ToolExecutor()
        messages = []
        ex.execute_tool_calls(
            [
                _tool_call("call_1", "MyTool"),
                _tool_call("call_2", "MyTool"),
            ],
            messages,
        )
        assert [m["role"] for m in messages] == ["tool", "tool"]
        assert [m["tool_call_id"] for m in messages] == ["call_1", "call_2"]

    def test_handle_tool_calls_appends_assistant_and_tool_messages(monkeypatch):
        """``handle_tool_calls`` appends the assistant + tool messages."""
        _register(monkeypatch, "MyTool", "r")
        ex = ToolExecutor()
        messages = []
        ex.handle_tool_calls(
            {0: {"id": "call_1", "name": "MyTool", "arguments": "{}"}},
            messages,
            full_content="hello",
        )
        assert len(messages) == 2
        assert messages[0]["role"] == "assistant"
        assert messages[0]["content"] == "hello"
        assert [c["id"] for c in messages[0]["tool_calls"]] == ["call_1"]
        assert messages[1]["role"] == "tool"
        assert messages[1]["tool_call_id"] == "call_1"
