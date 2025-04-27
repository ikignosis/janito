# janito/agent/tool_registry.py
from janito.agent.tool_base import ToolBase
from janito.agent.openai_schema_generator import generate_openai_function_schema

_tool_registry = {}


def register_tool(tool=None, *, name: str = None):
    if tool is None:
        return lambda t: register_tool(t, name=name)
    override_name = name
    if not (isinstance(tool, type) and issubclass(tool, ToolBase)):
        raise TypeError("Tool must be a class derived from ToolBase.")
    instance = tool()
    if not hasattr(instance, "run") or not callable(instance.run):
        raise TypeError(
            f"Tool '{tool.__name__}' must implement a callable 'call' method."
        )
    tool_name = override_name or instance.name
    if tool_name in _tool_registry:
        raise ValueError(f"Tool '{tool_name}' is already registered.")
    schema = generate_openai_function_schema(instance.run, tool_name, tool_class=tool)
    _tool_registry[tool_name] = {
        "function": instance.run,
        "description": schema["description"],
        "parameters": schema["parameters"],
        "class": tool,
        "instance": instance,
    }
    return tool


def get_tool_schemas():
    schemas = []
    for name, entry in _tool_registry.items():
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": entry["description"],
                    "parameters": entry["parameters"],
                },
            }
        )
    return schemas
