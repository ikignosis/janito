import os
import json
import traceback
from janito.agent.tools.tool_base import ToolBase

class ToolHandler:
    _tool_registry = {}

    def __init__(self, verbose=False, enable_tools=True):
        self.verbose = verbose
        self.tools = []
        self.enable_tools = enable_tools

    @classmethod
    def register_tool(cls, tool=None, *, name: str = None):
        # allow optional name override for PascalCase tool naming
        if tool is None:
            return lambda t: cls.register_tool(t, name=name)
        import inspect
        import typing
        from typing import get_origin, get_args

        override_name = name
        # support classes deriving from ToolBase
        if isinstance(tool, type) and issubclass(tool, ToolBase):
            instance = tool()
            func = instance.call
            default_name = tool.__name__
            name = override_name or default_name
            description = tool.__doc__ or func.__doc__ or ""
        else:
            func = tool
            default_name = func.__name__
            name = override_name or default_name
            description = func.__doc__ or ""

        sig = inspect.signature(func)
        params_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        for param_name, param in sig.parameters.items():
            if param.annotation is param.empty:
                raise TypeError(f"Parameter '{param_name}' in tool '{name}' is missing a type hint.")
            param_type = param.annotation
            schema = {}

            # Handle typing.Optional, typing.List, typing.Literal, etc.
            origin = get_origin(param_type)
            args = get_args(param_type)

            if origin is typing.Union and type(None) in args:
                # Optional[...] type
                main_type = args[0] if args[1] is type(None) else args[1]
                origin = get_origin(main_type)
                args = get_args(main_type)
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

            # Optionally add description if available in docstring (not implemented here)
            params_schema["properties"][param_name] = schema
            if param.default is param.empty:
                params_schema["required"].append(param_name)

        # register the bound call function
        cls._tool_registry[name] = {
            "function": func,
            "description": description,
            "parameters": params_schema
        }
        return tool

    def register(self, func):
        self.tools.append(func)
        return func

    def get_tools(self):
        return self.tools

    def get_tool_schemas(self):
        if not getattr(self, 'enable_tools', True):
            return []
        schemas = []
        for name, entry in self._tool_registry.items():
            schemas.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": entry["description"],
                    "parameters": entry["parameters"]
                }
            })
        return schemas

    def handle_tool_call(self, tool_call, on_progress=None):
        import uuid
        call_id = getattr(tool_call, 'id', None) or str(uuid.uuid4())
        tool_entry = self._tool_registry.get(tool_call.function.name)
        if not tool_entry:
            return f"Unknown tool: {tool_call.function.name}"
        func = tool_entry["function"]
        args = json.loads(tool_call.function.arguments)
        if self.verbose:
            print(f"[Tool Call] {tool_call.function.name} called with arguments: {args}")
        import inspect
        sig = inspect.signature(func)
        if on_progress:
            on_progress({
                'event': 'start',
                'call_id': call_id,
                'tool': tool_call.function.name,
                'args': args
            })
        if 'on_progress' in sig.parameters and on_progress is not None:
            args['on_progress'] = on_progress
        try:
            result = func(**args)
        except Exception as e:
            import traceback
            error_message = f"[Tool Error] {type(e).__name__}: {e}\n" + traceback.format_exc()
            result = error_message
        if self.verbose:
            preview = result
            if isinstance(result, str):
                lines = result.splitlines()
                if len(lines) > 10:
                    preview = "\n".join(lines[:10]) + "\n... (truncated)"
                elif len(result) > 500:
                    preview = result[:500] + "... (truncated)"
            print(f"[Tool Result] {tool_call.function.name} returned:\n{preview}")
        if on_progress:
            on_progress({
                'event': 'finish',
                'call_id': call_id,
                'tool': tool_call.function.name,
                'args': args,
                'result': result
            })
        return result

def _pytype_to_json_type(pytype):
    import typing
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
