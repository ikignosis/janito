import types
import json
import pytest
from janito.agent import tool_registry
from janito.agent.tool_base import ToolBase


class DummyTool(ToolBase):
    name = "dummy"

    def call(self, a, b) -> str:
        """
        Add two numbers as strings.

        Parameters:
            a: First number
            b: Second number
        Returns:
            str: The sum as a string
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
        tool_registry.handle_tool_call(tool_call)
    print("Validation error (missing param):", excinfo.value)

    tool_call2 = make_tool_call("dummy", {"a": 1, "b": 2, "c": 3})  # extra 'c'
    with pytest.raises(TypeError) as excinfo2:
        tool_registry.handle_tool_call(tool_call2)
    print("Validation error (extra param):", excinfo2.value)


if __name__ == "__main__":
    test_handle_tool_call_wrong_params()
