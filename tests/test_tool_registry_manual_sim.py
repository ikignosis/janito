import types
import json
import pytest
from janito.agent import tool_registry
from janito.agent.tool_base import ToolBase


class DummyTool(ToolBase):
    """
    Dummy tool for testing.

    Args:
        a (int): First number.
        b (int): Second number.

    Returns:
        str: The sum as a string.
    """

    name = "dummy"

    def run(self, a: int, b: int) -> str:
        """
        Adds two numbers as strings.
        """
        return str(a + b)


tool_registry.register_tool(DummyTool)


def make_tool_call(name, args):
    ToolCall = types.SimpleNamespace
    Function = types.SimpleNamespace
    return ToolCall(function=Function(name=name, arguments=json.dumps(args)))


def test_handle_tool_call_wrong_params():
    tool_call = make_tool_call("dummy", {"a": 1})  # missing 'b'
    with pytest.raises(TypeError) as excinfo:
        from janito.agent.tool_executor import ToolExecutor

        tool_entry = tool_registry._tool_registry[tool_call.function.name]
        ToolExecutor().execute(tool_entry, tool_call)
    print("Validation error (missing param):", excinfo.value)

    tool_call2 = make_tool_call("dummy", {"a": 1, "b": 2, "c": 3})  # extra 'c'
    with pytest.raises(TypeError) as excinfo2:
        tool_entry2 = tool_registry._tool_registry[tool_call2.function.name]
        ToolExecutor().execute(tool_entry2, tool_call2)
    print("Validation error (extra param):", excinfo2.value)


if __name__ == "__main__":
    test_handle_tool_call_wrong_params()
