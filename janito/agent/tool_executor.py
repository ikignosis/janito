# janito/agent/tool_executor.py
"""
ToolExecutor: Responsible for executing tools, validating arguments, handling errors, and reporting progress.
"""

import json
import inspect
from janito.agent.tool_base import ToolBase


class ToolExecutor:
    def __init__(self, message_handler=None, verbose=False):
        self.message_handler = message_handler
        self.verbose = verbose

    def execute(self, tool_entry, tool_call):
        import uuid

        call_id = getattr(tool_call, "id", None) or str(uuid.uuid4())
        func = tool_entry["function"]
        args = json.loads(tool_call.function.arguments)
        if self.verbose:
            print(
                f"[ToolExecutor] {tool_call.function.name} called with arguments: {args}"
            )
        instance = None
        if hasattr(func, "__self__") and isinstance(func.__self__, ToolBase):
            instance = func.__self__
            if self.message_handler:
                instance._progress_callback = self.message_handler.handle_message
        # Emit tool_call event before calling the tool
        if self.message_handler:
            self.message_handler.handle_message(
                {
                    "type": "tool_call",
                    "tool": tool_call.function.name,
                    "call_id": call_id,
                    "arguments": args,
                }
            )
        # Argument validation
        sig = inspect.signature(func)
        try:
            sig.bind(**args)
        except TypeError as e:
            error_msg = f"Argument validation error for tool '{tool_call.function.name}': {str(e)}"
            if self.message_handler:
                self.message_handler.handle_message(
                    {
                        "type": "tool_error",
                        "tool": tool_call.function.name,
                        "call_id": call_id,
                        "error": error_msg,
                    }
                )
            raise TypeError(error_msg)
        # Execute tool
        try:
            result = func(**args)
            if self.message_handler:
                self.message_handler.handle_message(
                    {
                        "type": "tool_result",
                        "tool": tool_call.function.name,
                        "call_id": call_id,
                        "result": result,
                    }
                )
            return result
        except Exception as e:
            if self.message_handler:
                self.message_handler.handle_message(
                    {
                        "type": "tool_error",
                        "tool": tool_call.function.name,
                        "call_id": call_id,
                        "error": str(e),
                    }
                )
            raise
