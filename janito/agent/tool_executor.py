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

        call_id = getattr(tool_call, "id", None)
        if call_id is None:
            raise ValueError("Tool call is missing required 'id' from server.")
        func = tool_entry["function"]
        args = arguments
        if runtime_config.get("no_tools_tracking", False):
            tool_call_reason = None
        else:
            tool_call_reason = args.pop(
                "tool_call_reason", None
            )  # Extract and remove 'tool_call_reason' if present

        self._maybe_log_tool_call(tool_call, args, tool_call_reason)
        instance = self._maybe_set_progress_callback(func)
        self._emit_tool_call_event(tool_call, call_id, args, tool_call_reason)
        self._validate_arguments(func, args, tool_call, call_id, tool_call_reason)
        try:
            result = func(**args)
            self._emit_tool_result_event(tool_call, call_id, result, tool_call_reason)
            self._record_tool_usage(tool_call, args, result)
            return result
        except Exception as e:
            self._emit_tool_error_event(tool_call, call_id, str(e), tool_call_reason)
            raise

    def _maybe_log_tool_call(self, tool_call, args, tool_call_reason):
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

    def _maybe_set_progress_callback(self, func):
        instance = None
        if hasattr(func, "__self__") and isinstance(func.__self__, ToolBase):
            instance = func.__self__
            if self.message_handler:
                instance._progress_callback = self.message_handler.handle_message
        return instance

    def _emit_tool_call_event(self, tool_call, call_id, args, tool_call_reason):
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

    def _validate_arguments(self, func, args, tool_call, call_id, tool_call_reason):
        sig = inspect.signature(func)
        try:
            sig.bind(**args)
        except TypeError as e:
            error_msg = f"Argument validation error for tool '{tool_call.function.name}': {str(e)}"
            self._emit_tool_error_event(tool_call, call_id, error_msg, tool_call_reason)
            raise TypeError(error_msg)

    def _emit_tool_result_event(self, tool_call, call_id, result, tool_call_reason):
        if self.message_handler:
            result_event = {
                "type": "tool_result",
                "tool": tool_call.function.name,
                "call_id": call_id,
                "result": result,
            }
            if tool_call_reason and not runtime_config.get("no_tools_tracking", False):
                result_event["tool_call_reason"] = tool_call_reason
            self.message_handler.handle_message(result_event)

    def _emit_tool_error_event(self, tool_call, call_id, error, tool_call_reason):
        if self.message_handler:
            error_event = {
                "type": "tool_error",
                "tool": tool_call.function.name,
                "call_id": call_id,
                "error": error,
            }
            if tool_call_reason and not runtime_config.get("no_tools_tracking", False):
                error_event["tool_call_reason"] = tool_call_reason
            self.message_handler.handle_message(error_event)

    def _record_tool_usage(self, tool_call, args, result):
        try:
            from janito.agent.tool_use_tracker import ToolUseTracker

            ToolUseTracker().record(tool_call.function.name, dict(args), result)
        except Exception as e:
            if runtime_config.get("verbose", False):
                print(f"[ToolExecutor] ToolUseTracker record failed: {e}")
