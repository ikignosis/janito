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
        self.tool_name = tool_name or getattr(func, "tool_name", func.__name__)
        self._description = description or func.__doc__ or f"Tool: {self.tool_name}"
        self.permissions = ToolPermissions(read=True, write=True, execute=True)

    def run(
        self,
        path: str = None,
        content: str = None,
        overwrite: bool = None,
        sources: str = None,
        target: str = None,
        recursive: bool = None,
        from_line: int = None,
        to_line: int = None,
        search_text: str = None,
        replacement_text: str = None,
        use_regex: bool = None,
        case_sensitive: bool = None,
        max_depth: int = None,
        include_gitignored: bool = None,
        timeout: int = None,
        require_confirmation: bool = None,
        data: dict = None,
        title: str = None,
        width: int = None,
        height: int = None,
        query: str = None,
        paths: str = None,
        src_path: str = None,
        dest_path: str = None,
        code: str = None,
        pattern: str = None,
    ) -> str:
        """Execute the wrapped function."""
        # Build kwargs from non-None parameters
        import inspect

        sig = inspect.signature(self._func)
        filtered_kwargs = {}

        # Map parameter names to their actual values
        param_map = {
            "path": path,
            "content": content,
            "overwrite": overwrite,
            "sources": sources,
            "target": target,
            "recursive": recursive,
            "from_line": from_line,
            "to_line": to_line,
            "search_text": search_text,
            "replacement_text": replacement_text,
            "use_regex": use_regex,
            "case_sensitive": case_sensitive,
            "max_depth": max_depth,
            "include_gitignored": include_gitignored,
            "timeout": timeout,
            "require_confirmation": require_confirmation,
            "data": data,
            "title": title,
            "width": width,
            "height": height,
            "query": query,
            "paths": paths,
            "src_path": src_path,
            "dest_path": dest_path,
            "code": code,
            "pattern": pattern,
        }

        # Only include parameters that exist in the function signature
        for name, param in sig.parameters.items():
            if name in param_map and param_map[name] is not None:
                filtered_kwargs[name] = param_map[name]

        result = self._func(**filtered_kwargs)
        return str(result) if result is not None else ""

    def get_signature(self) -> Dict[str, Any]:
        """Get function signature for documentation."""
        sig = inspect.signature(self._func)
        type_hints = get_type_hints(self._func)

        params = {}
        for name, param in sig.parameters.items():
            param_info = {
                "type": str(type_hints.get(name, Any)),
                "default": (
                    param.default if param.default != inspect.Parameter.empty else None
                ),
                "required": param.default == inspect.Parameter.empty,
            }
            params[name] = param_info

        return {
            "name": self.tool_name,
            "description": self._description,
            "parameters": params,
            "return_type": str(type_hints.get("return", Any)),
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
    # Resolve tool_name in outer scope
    resolved_tool_name = tool_name or getattr(func, "tool_name", func.__name__)

    class DynamicFunctionTool(FunctionToolAdapter):
        permissions = ToolPermissions(read=True, write=True, execute=True)
        tool_name = resolved_tool_name

        def __init__(self):
            super().__init__(func, DynamicFunctionTool.tool_name, description)

    return DynamicFunctionTool
