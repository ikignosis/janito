import types
import json
from janito.agent import tool_registry
from janito.agent.tool_base import ToolBase


def make_tool_call(name, args):
    ToolCall = types.SimpleNamespace
    Function = types.SimpleNamespace
    return ToolCall(function=Function(name=name, arguments=json.dumps(args)))


# Acceptable: Args:
class ToolArgs(ToolBase):
    """
    Add two numbers.
    Args:
        a: First
        b: Second
    Returns:
        str: Sum
    """

    name = "tool_args"

    def run(self, a: int, b: int) -> str:
        return str(a + b)


tool_registry.register_tool(ToolArgs)


# Acceptable: Arguments (type):
class ToolArguments(ToolBase):
    """
    Multiply two numbers.
    Arguments:
        x (int): First
        y (int): Second
    Returns:
        str: Product
    """

    name = "tool_arguments"

    def run(self, x: int, y: int) -> str:
        return str(x * y)


tool_registry.register_tool(ToolArguments)


# Acceptable: Params -
class ToolParams(ToolBase):
    """
    Concatenate.
    Params:
        foo - First
        bar - Second
    Returns:
        str: Result
    """

    name = "tool_params"

    def run(self, foo: int, bar: int) -> str:
        return str(foo) + str(bar)


tool_registry.register_tool(ToolParams)


# Acceptable: Parameters (no colon)
class ToolParameters(ToolBase):
    """
    Subtract.
    Parameters
        p: Minuend
        q: Subtrahend
    Returns:
        str: Difference
    """

    name = "tool_parameters"

    def run(self, p: int, q: int) -> str:
        return str(p - q)


tool_registry.register_tool(ToolParameters)


def test_all_tools_registered():
    # Just check registration and schema, not execution
    schemas = tool_registry.get_tool_schemas()
    names = [s["function"]["name"] for s in schemas]
    assert set(
        ["tool_args", "tool_arguments", "tool_params", "tool_parameters"]
    ).issubset(set(names))
