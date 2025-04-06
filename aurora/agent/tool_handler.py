import os
import json
import traceback

class ToolHandler:
    _tool_registry = {}

    @classmethod
    def register_tool(cls, func):
        import inspect

        name = func.__name__
        description = func.__doc__ or ""

        sig = inspect.signature(func)
        params_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        # Simple docstring param description extraction
        param_docs = {}
        if func.__doc__:
            import re
            # Match lines like: param_name: description
            for line in func.__doc__.splitlines():
                match = re.match(r"\s*(\w+)\s*:\s*(.+)", line)
                if match:
                    param_docs[match.group(1)] = match.group(2).strip()

        for param_name, param in sig.parameters.items():
            # Enforce type hint presence
            if param.annotation is inspect.Parameter.empty:
                raise TypeError(f"Parameter '{param_name}' in tool '{name}' is missing a type hint.")

            # Enforce docstring description presence
            doc = param_docs.get(param_name, "")
            if not doc:
                raise ValueError(f"Parameter '{param_name}' in tool '{name}' is missing a docstring description.")

            # Map Python type to JSON Schema type
            py_type = param.annotation
            if py_type == str:
                json_type = "string"
            elif py_type == int:
                json_type = "integer"
            elif py_type == bool:
                json_type = "boolean"
            elif py_type == float:
                json_type = "number"
            else:
                # Default fallback
                json_type = "string"

            params_schema["properties"][param_name] = {
                "type": json_type,
                "description": doc
            }
            if param.default is inspect.Parameter.empty:
                params_schema["required"].append(param_name)

        cls._tool_registry[name] = {
            "function": func,
            "schema": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": params_schema
                }
            }
        }
        return func

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.tools = [entry["schema"] for entry in self._tool_registry.values()]

    def get_tools(self):
        return self.tools

    def handle_tool_call(self, tool_call, on_progress=None):
        tool_entry = self._tool_registry.get(tool_call.function.name)
        if not tool_entry:
            return f"Unknown tool: {tool_call.function.name}"
        func = tool_entry["function"]
        args = json.loads(tool_call.function.arguments)
        if self.verbose:
            print(f"[Tool Call] {tool_call.function.name} called with arguments: {args}")
        try:
            import inspect
            sig = inspect.signature(func)
            if on_progress:
                on_progress({
                    'event': 'start',
                    'tool': tool_call.function.name,
                    'args': args
                })
            if 'on_progress' in sig.parameters and on_progress is not None:
                args['on_progress'] = on_progress
            result = func(**args)
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
                    'tool': tool_call.function.name,
                    'args': args,
                    'result': result
                })
            return result
        except Exception as e:
            if on_progress:
                on_progress({
                    'event': 'finish',
                    'tool': tool_call.function.name,
                    'args': args,
                    'error': str(e)
                })
            error_message = f"Error executing tool '{tool_call.function.name}': {e}"
            if self.verbose:
                print(f"[Tool Error] {error_message}")
                traceback.print_exc()
            return error_message
