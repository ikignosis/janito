# janito/agent/tool_registry.py
import json
import typing
import inspect
from janito.agent.tools.tool_base import ToolBase

def _pytype_to_json_type(pytype):
    if pytype == int:
        return "integer"
    elif pytype == float:
        return "number"
    elif pytype == bool:
        return "boolean"
    elif pytype == dict:
        return "object"
    elif pytype == list or pytype == typing.List:
        return "array"
    else:
        return "string"

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
    description = tool.__doc__ or func.__doc__ or ""
    sig = inspect.signature(func)
    params_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }
    for param_name, param in sig.parameters.items():
        if param.annotation is param.empty:
            raise TypeError(f"Parameter '{param_name}' in tool '{tool_name}' is missing a type hint.")
        param_type = param.annotation
        schema = {}
        origin = typing.get_origin(param_type)
        args = typing.get_args(param_type)
        if origin is typing.Union and type(None) in args:
            main_type = args[0] if args[1] is type(None) else args[1]
            origin = typing.get_origin(main_type)
            args = typing.get_args(main_type)
            param_type = main_type
        else:
            main_type = param_type
        if origin is list or origin is typing.List:
            item_type = args[0] if args else str
            item_schema = {"type": _pytype_to_json_type(item_type)}
            schema = {"type": "array", "items": item_schema}
        elif origin is typing.Literal:
            schema = {"type": _pytype_to_json_type(type(args[0])), "enum": list(args)}
        elif main_type == int:
            schema = {"type": "integer"}
        elif main_type == float:
            schema = {"type": "number"}
        elif main_type == bool:
            schema = {"type": "boolean"}
        elif main_type == dict:
            schema = {"type": "object"}
        elif main_type == list:
            schema = {"type": "array", "items": {"type": "string"}}
        else:
            schema = {"type": "string"}
        # Add description from call method docstring if available
        if func.__doc__:
            try:
                import docstring_parser
                parsed = docstring_parser.parse(func.__doc__)
                param_descs = {p.arg_name: p.description.strip() if p.description else '' for p in parsed.params}
            except ImportError:
                raise ImportError("docstring_parser must be installed to parse parameter descriptions.")
            if param_name in param_descs and param_descs[param_name]:
                schema["description"] = param_descs[param_name]
            else:
                raise TypeError(f"Parameter '{param_name}' in tool '{tool_name}' is missing a docstring description.")
        params_schema["properties"][param_name] = schema
        if param.default is param.empty:
            params_schema["required"].append(param_name)
    _tool_registry[tool_name] = {
        "function": func,
        "description": description,
        "parameters": params_schema
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
    try:
        result = func(**args)
    except Exception as e:
        import traceback
        error_message = f"[Tool Error] {type(e).__name__}: {e}\n" + traceback.format_exc()
        if message_handler:
            message_handler.handle_message({'type': 'error', 'message': error_message})
        result = error_message
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
