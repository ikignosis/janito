import functools
import time
import threading
from typing import Any, Tuple

# Global tracking for decorator-based loop protection
_decorator_call_tracker = {}
_decorator_call_tracker_lock = threading.Lock()


def _normalize_key_value(key_field: str, key_value: Any) -> Any:
    """Normalize key values, especially paths, so different representations map to the same key."""
    if key_value is None:
        return None

    try:
        if isinstance(key_field, str) and "path" in key_field.lower():
            from janito.tools.tool_use_tracker import (
                normalize_path as _norm,  # reuse existing normalization
            )

            if isinstance(key_value, str):
                return _norm(key_value)
            if isinstance(key_value, (list, tuple)):
                return tuple(_norm(v) if isinstance(v, str) else v for v in key_value)
    except Exception:
        # Best-effort normalization – fall back to original value
        pass

    return key_value


def _get_param_value(func, args, kwargs, key_field: str):
    """Extract the watched parameter value from args/kwargs using function signature."""
    if key_field in kwargs:
        return kwargs[key_field]

    # Handle positional arguments by mapping to parameter names
    if len(args) > 1:  # args[0] is self
        import inspect

        try:
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            if key_field in param_names:
                idx = param_names.index(key_field)
                if idx < len(args):
                    return args[idx]
        except Exception:
            return None

    return None


def _determine_operation_name(func, args, kwargs, key_field: str) -> str:
    """Build the operation name for rate limiting, optionally including a normalized key value."""
    if key_field:
        raw_value = _get_param_value(func, args, kwargs, key_field)
        if raw_value is not None:
            norm_value = _normalize_key_value(key_field, raw_value)
            return f"{func.__name__}_{norm_value}"
    return func.__name__


def _check_and_record(
    op_name: str,
    current_time: float,
    time_window: float,
    max_calls: int,
    tool_instance: Any,
) -> Tuple[bool, str]:
    """Check loop limits for op_name and record the call. Returns (exceeded, message)."""
    with _decorator_call_tracker_lock:
        # Clean old timestamps
        if op_name in _decorator_call_tracker:
            _decorator_call_tracker[op_name] = [
                ts
                for ts in _decorator_call_tracker[op_name]
                if current_time - ts <= time_window
            ]

        # Check limit
        if (
            op_name in _decorator_call_tracker
            and len(_decorator_call_tracker[op_name]) >= max_calls
        ):
            if all(
                current_time - ts <= time_window
                for ts in _decorator_call_tracker[op_name]
            ):
                msg = (
                    f"Loop protection: Too many {op_name} operations in a short time period "
                    f"({max_calls} calls in {time_window}s). Please try a different approach or wait before retrying."
                )
                if hasattr(tool_instance, "report_error"):
                    try:
                        tool_instance.report_error(msg)
                    except Exception:
                        pass
                return True, msg

        # Record this call
        if op_name not in _decorator_call_tracker:
            _decorator_call_tracker[op_name] = []
        _decorator_call_tracker[op_name].append(current_time)

    return False, ""


def protect_against_loops(
    max_calls: int = 5, time_window: float = 10.0, key_field: str = None
):
    """
    Decorator that adds loop protection to tool run methods.

    Tracks calls within a sliding time window and prevents excessive repeated operations.
    When key_field is provided, the limit is applied per unique normalized value of that parameter
    (e.g., per-path protection for file tools).
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Methods should always have self; if not, execute directly.
            if not args:
                return func(*args, **kwargs)

            op_name = _determine_operation_name(func, args, kwargs, key_field)
            exceeded, msg = _check_and_record(
                op_name=op_name,
                current_time=time.time(),
                time_window=time_window,
                max_calls=max_calls,
                tool_instance=args[0],
            )
            if exceeded:
                return msg
            return func(*args, **kwargs)

        return wrapper

    return decorator
