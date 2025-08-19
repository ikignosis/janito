import functools
import time
import threading
from typing import Callable, Any
from janito.tools.loop_protection import LoopProtection
from janito.tools.tool_use_tracker import normalize_path


# Global tracking for decorator-based loop protection
_decorator_call_tracker = {}
_decorator_call_tracker_lock = threading.Lock()


def protect_against_loops(
    max_calls: int = 5, time_window: float = 10.0, key_field: str = None
):
    """
    Decorator that adds loop protection to tool run methods.

    This decorator monitors tool executions and prevents excessive calls within
    a configurable time window. It helps prevent infinite loops or excessive
    resource consumption when tools are called repeatedly.

    When the configured limits are exceeded, the decorator raises a RuntimeError
    with a descriptive message. This exception will propagate up the call stack
    unless caught by a try/except block in the calling code.

    The decorator works by:
    1. Tracking the number of calls to the decorated function
    2. Checking if the calls exceed the configured limits
    3. Raising a RuntimeError if a potential loop is detected
    4. Allowing the method to proceed normally if the operation is safe

    Args:
        max_calls (int): Maximum number of calls allowed within the time window.
                        Defaults to 5 calls.
        time_window (float): Time window in seconds for detecting excessive calls.
                            Defaults to 10.0 seconds.
        key_field (str, optional): The parameter name to use for key matching instead of function name.
                                 If provided, the decorator will track calls based on the value of this
                                 parameter rather than the function name. Useful for tools that operate
                                 on specific files or resources.

    Example:
        >>> @protect_against_loops(max_calls=3, time_window=5.0)
        >>> def run(self, path: str) -> str:
        >>>     # Implementation here
        >>>     pass

        >>> @protect_against_loops(max_calls=10, time_window=30.0)
        >>> def run(self, file_paths: list) -> str:
        >>>     # Implementation here
        >>>     pass

        >>> @protect_against_loops(max_calls=5, time_window=10.0, key_field='path')
        >>> def run(self, path: str) -> str:
        >>>     # This will track calls per unique path value
        >>>     pass

    Note:
        When loop protection is triggered, a RuntimeError will be raised with a
        descriptive message. This exception will propagate up the call stack
        unless caught by a try/except block in the calling code.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get the tool instance (self)
            if not args:
                # This shouldn't happen in normal usage as methods need self
                return func(*args, **kwargs)

            # Determine the operation key
            if key_field:
                # Use the key_field parameter value as the operation key
                key_value = None
                if key_field in kwargs:
                    key_value = kwargs[key_field]
                elif len(args) > 1:
                    # Handle positional arguments - need to map parameter names
                    import inspect

                    try:
                        sig = inspect.signature(func)
                        param_names = list(sig.parameters.keys())
                        if key_field in param_names:
                            field_index = param_names.index(key_field)
                            if field_index < len(args):
                                key_value = args[field_index]
                    except (ValueError, TypeError):
                        pass

                if key_value is not None:
                    op_name = f"{func.__name__}_{key_value}"
                else:
                    op_name = func.__name__
            else:
                # Use the function name as the operation name
                op_name = func.__name__

            # Check call limits
            current_time = time.time()

            with _decorator_call_tracker_lock:
                # Clean up old entries outside the time window
                if op_name in _decorator_call_tracker:
                    _decorator_call_tracker[op_name] = [
                        timestamp
                        for timestamp in _decorator_call_tracker[op_name]
                        if current_time - timestamp <= time_window
                    ]

                # Check if we're exceeding the limit
                if op_name in _decorator_call_tracker:
                    if len(_decorator_call_tracker[op_name]) >= max_calls:
                        # Check if all recent calls are within the time window
                        if all(
                            current_time - timestamp <= time_window
                            for timestamp in _decorator_call_tracker[op_name]
                        ):
                            # Return loop protection message as string instead of raising exception
                            error_msg = f"Loop protection: Too many {op_name} operations in a short time period ({max_calls} calls in {time_window}s). Please try a different approach or wait before retrying."

                            # Try to report the error through the tool's reporting mechanism
                            tool_instance = args[0] if args else None
                            if hasattr(tool_instance, "report_error"):
                                try:
                                    tool_instance.report_error(error_msg)
                                except Exception:
                                    pass  # If reporting fails, we still return the message

                            return error_msg

                # Record this call
                if op_name not in _decorator_call_tracker:
                    _decorator_call_tracker[op_name] = []
                _decorator_call_tracker[op_name].append(current_time)

            # Proceed with the original function
            return func(*args, **kwargs)

        return wrapper

    return decorator
