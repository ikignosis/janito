# janito/agent/tool_registry.py
import json
from janito.agent.tools.tool_base import ToolBase

from janito.agent.openai_schema_generator import generate_openai_function_schema

_tool_registry = {}

def register_tool(tool=None, *, name: str = None):
    if tool is None:
        return lambda t: register_tool(t, name=name)
    override_name = name
    if not (isinstance(tool, type) and issubclass(tool, ToolBase)):
        raise TypeError("Tool must be a class derived from ToolBase.")
    instance = tool()
    func = instance.call
    default_name = tool.__name__
    tool_name = override_name or default_name
    schema = generate_openai_function_schema(func, tool_name)


    _tool_registry[tool_name] = {
        "function": func,
        "description": schema["description"],
        "parameters": schema["parameters"]
    }
    return tool

def get_tool_schemas():
    schemas = []
    for name, entry in _tool_registry.items():
        schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": entry["description"],
                "parameters": entry["parameters"]
            }
        })
    return schemas

def handle_tool_call(tool_call, message_handler=None, verbose=False):
    import uuid
    call_id = getattr(tool_call, 'id', None) or str(uuid.uuid4())
    tool_entry = _tool_registry.get(tool_call.function.name)
    if not tool_entry:
        return f"Unknown tool: {tool_call.function.name}"
    func = tool_entry["function"]
    args = json.loads(tool_call.function.arguments)
    if verbose:
        print(f"[Tool Call] {tool_call.function.name} called with arguments: {args}")
    instance = None
    if hasattr(func, '__self__') and isinstance(func.__self__, ToolBase):
        instance = func.__self__
        if message_handler:
            instance._progress_callback = message_handler.handle_message
    # Emit tool_call event before calling the tool
    if message_handler:
        message_handler.handle_message({
            'type': 'tool_call',
            'tool': tool_call.function.name,
            'args': args,
            'call_id': call_id
        })
    try:
        result = func(**args)
    except Exception as e:
        import traceback  # Kept here: only needed on error
        error_message = f"[Tool Error] {type(e).__name__}: {e}\n" + traceback.format_exc()
        if message_handler:
            message_handler.handle_message({'type': 'error', 'message': error_message})
        result = error_message
    # Emit tool_result event after tool execution
    if message_handler:
        message_handler.handle_message({
            'type': 'tool_result',
            'tool': tool_call.function.name,
            'call_id': call_id,
            'result': result
        })
    if verbose:
        preview = result
        if isinstance(result, str):
            lines = result.splitlines()
            if len(lines) > 10:
                preview = "\n".join(lines[:10]) + "\n... (truncated)"
            elif len(result) > 500:
                preview = result[:500] + "... (truncated)"
        print(f"[Tool Result] {tool_call.function.name} returned:\n{preview}")
    if instance is not None:
        instance._progress_callback = None
    return result
