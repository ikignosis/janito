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
        """
        Register a tool class derived from ToolBase.
        Args:
            tool: The tool class (must inherit from ToolBase).
            name: Optional override for the tool name.
        Raises:
            TypeError: If the tool is not a subclass of ToolBase.
        """
        if tool is None:
            return lambda t: cls.register_tool(t, name=name)
        import inspect
        import typing
        from typing import get_origin, get_args

        override_name = name
        if not (isinstance(tool, type) and issubclass(tool, ToolBase)):
            raise TypeError("Tool must be a class derived from ToolBase.")
        instance = tool()
        func = instance.call
        default_name = tool.__name__
        name = override_name or default_name
        description = tool.__doc__ or func.__doc__ or ""

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

            # Add description from call method docstring if available (Google-style Args parsing)
            if func.__doc__:
                import re
                doc = func.__doc__
                args_section = re.search(r"Args:\s*(.*?)(?:\n\s*\w|Returns:|$)", doc, re.DOTALL)
                param_descs = {}
                if args_section:
                    args_text = args_section.group(1)
                    for match in re.finditer(r"(\w+) \([^)]+\): ([^\n]+)", args_text):
                        pname, pdesc = match.groups()
                        param_descs[pname] = pdesc.strip()
                if param_name in param_descs:
                    schema["description"] = param_descs[param_name]
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
        # Set progress callback on tool instance if possible
        instance = None
        if hasattr(func, '__self__') and isinstance(func.__self__, ToolBase):
            instance = func.__self__
            instance._progress_callback = on_progress
        if on_progress:
            on_progress({
                'event': 'start',
                'call_id': call_id,
                'tool': tool_call.function.name,
                'args': args
            })
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
        # Clean up progress callback
        if instance is not None:
            instance._progress_callback = None
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
