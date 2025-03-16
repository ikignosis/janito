"""
Decorators for janito tools.
"""
import functools
import string
from typing import Any, Callable, Dict, Optional


class ToolMetaFormatter(string.Formatter):
    """Custom string formatter that handles conditional expressions in format strings."""
    
    def get_value(self, key, args, kwargs):
        """Override to handle conditional expressions."""
        if key in kwargs:
            return kwargs[key]
        
        # Try to evaluate the key as a Python expression
        try:
            # Create a safe local namespace with only the parameters
            return eval(key, {"__builtins__": {}}, kwargs)
        except Exception:
            return f"[{key}]"


def tool_meta(label: str):
    """
    Decorator to add metadata to a tool function.
    
    Args:
        label: A format string that can reference function parameters.
              Example: "Finding files {pattern}, on {root_dir}"
              
    Returns:
        Decorated function with metadata attached
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Attach metadata to the function
        wrapper._tool_meta = {
            'label': label
        }
        
        return wrapper
    
    return decorator


def tool(func: Callable):
    """
    Basic decorator for tool functions.
    
    This decorator marks a function as a tool and can be used for
    simpler tools that don't need additional metadata.
    
    Returns:
        Decorated function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    return wrapper


def format_tool_label(func: Callable, tool_input: Dict[str, Any]) -> Optional[str]:
    """
    Format the tool label using the function's parameters.
    
    Args:
        func: The tool function
        tool_input: Input parameters for the tool
        
    Returns:
        Formatted label string or None if no label is defined
    """
    if not hasattr(func, '_tool_meta') or 'label' not in func._tool_meta:
        return None
    
    # Get the label template
    label_template = func._tool_meta['label']
    
    # Format the label with the parameters
    try:
        formatter = ToolMetaFormatter()
        return formatter.format(label_template, **tool_input)
    except Exception:
        return f"{func.__name__}"
