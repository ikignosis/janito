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

        for param_name, param in sig.parameters.items():
            if param.annotation is param.empty:
                raise TypeError(f"Parameter '{param_name}' in tool '{name}' is missing a type hint.")
            param_type = param.annotation
            json_type = "string"
            if param_type == int:
                json_type = "integer"
            elif param_type == float:
                json_type = "number"
            elif param_type == bool:
                json_type = "boolean"
            elif param_type == dict:
                json_type = "object"
            elif param_type == list:
                json_type = "array"
            params_schema["properties"][param_name] = {"type": json_type}
            if param.default is param.empty:
                params_schema["required"].append(param_name)

        cls._tool_registry[name] = {
            "function": func,
            "description": description,
            "parameters": params_schema
        }
        return func

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.tools = []

    def register(self, func):
        self.tools.append(func)
        return func

    def get_tools(self):
        return self.tools

    def handle_tool_call(self, tool_call, on_progress=None):
        print(f"[ToolHandler] handle_tool_call invoked for: {tool_call.function.name}")  # Debug print
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
            tb = traceback.format_exc()
            if on_progress:
                on_progress({
                    'event': 'finish',
                    'tool': tool_call.function.name,
                    'args': args,
                    'error': str(e),
                    'traceback': tb
                })
            return f"Error running tool {tool_call.function.name}: {e}"