"""
Tool decorator for explicitly marking functions as AI tools.

This module provides a decorator that can be used to explicitly mark
functions as tools that should be included in the auto-discovery process.
"""

import functools
from collections.abc import Callable
from typing import Any


def tool(
    obj: Callable | type | None = None, *, permissions: str = ""
) -> Callable | type:
    """
    Decorator to explicitly mark a function or class as an AI tool.

    Functions or classes decorated with @tool will be automatically discovered
    and included in the tools registry when their toolset is loaded.

    For functions:
        - The function itself becomes the tool
        - Permissions are stored on the function object

    For classes (that inherit from BaseTool):
        - The class must implement a `run` method
        - An instance is created and the `run` method is called
        - Permissions are stored on the class

    Args:
        obj (Callable or Type, optional): The function or class to mark as a tool
        permissions (str): Permission string indicating required permissions:
            - "r": read access (files, directories, system info)
            - "w": write access (create, modify, delete files/directories)
            - "x": execute access (run commands, scripts, programs)
            - Combinations like "rw", "rx", "rwx" are allowed

    Returns:
        Callable or Type: The original function/class with _is_tool and _tool_permissions attributes set
    """

    def decorator(obj: Callable | type) -> Callable | type:
        # Mark the object as a tool
        obj._is_tool = True  # type: ignore[attr-defined]

        if isinstance(obj, type):
            # It's a class
            obj._tool_permissions = permissions  # type: ignore[attr-defined]
        else:
            # It's a function
            obj._tool_permissions = permissions  # type: ignore[attr-defined]

            # Preserve the original function's metadata
            @functools.wraps(obj)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                return obj(*args, **kwargs)

            # Also mark the wrapper as a tool and set permissions
            wrapper._is_tool = True  # type: ignore[attr-defined]
            wrapper._tool_permissions = permissions  # type: ignore[attr-defined]

            return wrapper

        return obj

    # Handle both @tool and @tool(permissions="...") usage
    if obj is None:
        return decorator
    else:
        return decorator(obj)


def is_tool(func: Callable) -> bool:
    """
    Check if a function is marked as a tool.

    Args:
        func (Callable): The function to check

    Returns:
        bool: True if the function is marked as a tool, False otherwise
    """
    return getattr(func, "_is_tool", False)
