# janito/agent/tool_registry.py
import json
from janito.agent.tool_base import ToolBase
from janito.agent.openai_schema_generator import generate_openai_function_schema
import inspect

_tool_registry = {}


def register_tool(tool=None, *, name: str = None):
    if tool is None:
        return lambda t: register_tool(t, name=name)
    override_name = name
    if not (isinstance(tool, type) and issubclass(tool, ToolBase)):
        raise TypeError("Tool must be a class derived from ToolBase.")
    instance = tool()
    if not hasattr(instance, "call") or not callable(instance.call):
        raise TypeError(
            f"Tool '{tool.__name__}' must implement a callable 'call' method."
        )
    tool_name = override_name or instance.name
    if tool_name in _tool_registry:
        raise ValueError(f"Tool '{tool_name}' is already registered.")
    schema = generate_openai_function_schema(instance.call, tool_name, tool_class=tool)
    _tool_registry[tool_name] = {
        "function": instance.call,
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


def handle_tool_call(tool_call, message_handler=None, verbose=False):
    import uuid

    call_id = getattr(tool_call, "id", None) or str(uuid.uuid4())
    tool_entry = _tool_registry.get(tool_call.function.name)
    if not tool_entry:
        return f"Unknown tool: {tool_call.function.name}"
    func = tool_entry["function"]
    args = json.loads(tool_call.function.arguments)
    if verbose:
        print(f"[Tool Call] {tool_call.function.name} called with arguments: {args}")
    instance = None
    if hasattr(func, "__self__") and isinstance(func.__self__, ToolBase):
        instance = func.__self__
        if message_handler:
            instance._progress_callback = message_handler.handle_message
    # Emit tool_call event before calling the tool
    if message_handler:
        message_handler.handle_message(
            {
                "type": "tool_call",
                "tool": tool_call.function.name,
                "call_id": call_id,
                "arguments": args,
            }
        )
    # --- Argument validation start ---
    sig = inspect.signature(func)
    try:
        sig.bind(**args)
    except TypeError as e:
        error_msg = (
            f"Argument validation error for tool '{tool_call.function.name}': {str(e)}"
        )
        if message_handler:
            message_handler.handle_message(
                {
                    "type": "tool_error",
                    "tool": tool_call.function.name,
                    "call_id": call_id,
                    "error": error_msg,
                }
            )
        raise TypeError(error_msg)
    # --- Argument validation end ---
    try:
        result = func(**args)
        if message_handler:
            message_handler.handle_message(
                {
                    "type": "tool_result",
                    "tool": tool_call.function.name,
                    "call_id": call_id,
                    "result": result,
                }
            )
        return result
    except Exception as e:
        if message_handler:
            message_handler.handle_message(
                {
                    "type": "tool_error",
                    "tool": tool_call.function.name,
                    "call_id": call_id,
                    "error": str(e),
                }
            )
        raise
