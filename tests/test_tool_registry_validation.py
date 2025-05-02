import pytest
import types
import json
from janito.agent import tool_registry
from janito.agent.tool_executor import ToolExecutor


class DummyTool:
    def __call__(self, a, b):
        return a + b


def make_tool_call(name, args):
    # Simulate a tool_call object with .function.name and .function.arguments
    ToolCall = types.SimpleNamespace
    Function = types.SimpleNamespace
    return ToolCall(function=Function(name=name, arguments=json.dumps(args)))


def test_handle_tool_call_valid_args():
    # Register dummy tool
    tool_registry._tool_registry["dummy"] = {"function": DummyTool()}
    tool_call = make_tool_call("dummy", {"a": 1, "b": 2})
    tool_entry = tool_registry._tool_registry[tool_call.function.name]
    args = json.loads(tool_call.function.arguments)
    result = ToolExecutor().execute(tool_entry, tool_call, args)
    assert result == 3


def test_handle_tool_call_missing_arg():
    tool_registry._tool_registry["dummy"] = {"function": DummyTool()}
    tool_call = make_tool_call("dummy", {"a": 1})
    with pytest.raises(TypeError) as excinfo:
        tool_entry = tool_registry._tool_registry[tool_call.function.name]
        args = json.loads(tool_call.function.arguments)
        ToolExecutor().execute(tool_entry, tool_call, args)
    assert "missing a required argument" in str(excinfo.value)


def test_handle_tool_call_extra_arg():
    tool_registry._tool_registry["dummy"] = {"function": DummyTool()}
    tool_call = make_tool_call("dummy", {"a": 1, "b": 2, "c": 3})
    with pytest.raises(TypeError) as excinfo:
        tool_entry = tool_registry._tool_registry[tool_call.function.name]
        args = json.loads(tool_call.function.arguments)
        ToolExecutor().execute(tool_entry, tool_call, args)
    assert "got an unexpected keyword argument" in str(excinfo.value)
