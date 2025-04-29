# janito/agent/tool_executor.py
"""
ToolExecutor: Responsible for executing tools, validating arguments, handling errors, and reporting progress.
"""

from janito.i18n import tr
import inspect
from janito.agent.tool_base import ToolBase
from janito.agent.runtime_config import runtime_config


class ToolExecutor:
    def __init__(self, message_handler=None):
        self.message_handler = message_handler

    def execute(self, tool_entry, tool_call, arguments):
        import uuid

        call_id = getattr(tool_call, "id", None) or str(uuid.uuid4())
        func = tool_entry["function"]
        args = arguments
        if runtime_config.get("no_tools_tracking", False):
            tool_call_reason = None
        else:
            tool_call_reason = args.pop(
                "tool_call_reason", None
            )  # Extract and remove 'tool_call_reason' if present
        # Record tool usage
        try:
            from janito.agent.tool_use_tracker import ToolUseTracker

            ToolUseTracker().record(tool_call.function.name, dict(args))
        except Exception as e:
            if runtime_config.get("verbose", False):
                print(f"[ToolExecutor] ToolUseTracker record failed: {e}")

        verbose = runtime_config.get("verbose", False)
        if verbose:
            print(
                tr(
                    "[ToolExecutor] {tool_name} called with arguments: {args}",
                    tool_name=tool_call.function.name,
                    args=args,
                )
            )
        if runtime_config.get("verbose_reason", False) and tool_call_reason:
            print(
                tr(
                    "[ToolExecutor] Reason for call: {tool_call_reason}",
                    tool_call_reason=tool_call_reason,
                )
            )
        instance = None
        if hasattr(func, "__self__") and isinstance(func.__self__, ToolBase):
            instance = func.__self__
            if self.message_handler:
                instance._progress_callback = self.message_handler.handle_message
        # Emit tool_call event before calling the tool
        if self.message_handler:
            event = {
                "type": "tool_call",
                "tool": tool_call.function.name,
                "call_id": call_id,
                "arguments": args,
            }
            if tool_call_reason and not runtime_config.get("no_tools_tracking", False):
                event["tool_call_reason"] = tool_call_reason
            self.message_handler.handle_message(event)
        # Argument validation
        sig = inspect.signature(func)
        try:
            sig.bind(**args)
        except TypeError as e:
            error_msg = f"Argument validation error for tool '{tool_call.function.name}': {str(e)}"
            if self.message_handler:
                error_event = {
                    "type": "tool_error",
                    "tool": tool_call.function.name,
                    "call_id": call_id,
                    "error": error_msg,
                }
                if tool_call_reason and not runtime_config.get(
                    "no_tools_tracking", False
                ):
                    error_event["tool_call_reason"] = tool_call_reason
                self.message_handler.handle_message(error_event)
            raise TypeError(error_msg)
        # Execute tool
        try:
            result = func(**args)
            if self.message_handler:
                result_event = {
                    "type": "tool_result",
                    "tool": tool_call.function.name,
                    "call_id": call_id,
                    "result": result,
                }
                if tool_call_reason and not runtime_config.get(
                    "no_tools_tracking", False
                ):
                    result_event["tool_call_reason"] = tool_call_reason
                self.message_handler.handle_message(result_event)
            return result
        except Exception as e:
            if self.message_handler:
                error_event = {
                    "type": "tool_error",
                    "tool": tool_call.function.name,
                    "call_id": call_id,
                    "error": str(e),
                }
                if tool_call_reason and not runtime_config.get(
                    "no_tools_tracking", False
                ):
                    error_event["tool_call_reason"] = tool_call_reason
                self.message_handler.handle_message(error_event)
            raise
