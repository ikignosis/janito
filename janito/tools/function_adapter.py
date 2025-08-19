"""
Function-to-Tool adapter for core plugins.

This module provides a way to wrap function-based tools into proper ToolBase classes.
"""

import inspect
from typing import Any, Dict, List, Optional, get_type_hints
from janito.tools.tool_base import ToolBase, ToolPermissions


class FunctionToolAdapter(ToolBase):
    """Adapter that wraps a function into a ToolBase class."""
    
    def __init__(self, func, tool_name: str = None, description: str = None):
        super().__init__()
        self._func = func
        self.tool_name = tool_name or func.__name__
        self._description = description or func.__doc__ or f"Tool: {self.tool_name}"
        self.permissions = ToolPermissions(read=True, write=True, execute=True)
        
    def run(self, **kwargs) -> Any:
        """Execute the wrapped function."""
        return self._func(**kwargs)
    
    def get_signature(self) -> Dict[str, Any]:
        """Get function signature for documentation."""
        sig = inspect.signature(self._func)
        type_hints = get_type_hints(self._func)
        
        params = {}
        for name, param in sig.parameters.items():
            param_info = {
                "type": str(type_hints.get(name, Any)),
                "default": param.default if param.default != inspect.Parameter.empty else None,
                "required": param.default == inspect.Parameter.empty,
            }
            params[name] = param_info
            
        return {
            "name": self.tool_name,
            "description": self._description,
            "parameters": params,
            "return_type": str(type_hints.get("return", Any))
        }


def create_function_tool(func, tool_name: str = None, description: str = None) -> type:
    """
    Create a ToolBase class from a function.
    
    Args:
        func: The function to wrap
        tool_name: Optional custom tool name
        description: Optional custom description
        
    Returns:
        A ToolBase subclass that wraps the function
    """
    
    class DynamicFunctionTool(FunctionToolAdapter):
        def __init__(self):
            super().__init__(func, tool_name, description)
    
    return DynamicFunctionTool