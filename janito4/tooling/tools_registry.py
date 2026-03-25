"""
Main tools module for AI function calling.

This module provides easy access to all available tools and their schemas.
"""

from typing import Dict, Any, List, Callable, Optional, get_type_hints, Union
from ..tools import discover_toolsets
import inspect
import re


# Configuration for auto-loading toolsets
AUTOLOAD_TOOLSETS = ["files", "system"]

# Track loaded toolsets to avoid duplicates
_loaded_toolsets = set(AUTOLOAD_TOOLSETS.copy())


def get_function_schema(func: Callable) -> Dict[str, Any]:
    """
    Generate a JSON schema for a function based on its signature and docstring.
    
    Args:
        func (Callable): The function to generate a schema for
        
    Returns:
        Dict[str, Any]: OpenAI function calling schema
    """
    # Get function name
    func_name = func.__name__
    
    # Get function docstring
    docstring = inspect.getdoc(func) or ""
    
    # Extract main description (first line or paragraph)
    description = docstring.split("\n")[0] if docstring else f"Function {func_name}"
    
    # Parse docstring for parameter descriptions
    param_descriptions = {}
    if docstring:
        # Look for Args section in docstring
        args_match = re.search(r'Args:\s*(.*?)(?:\n\s*\w+:|\Z)', docstring, re.DOTALL | re.IGNORECASE)
        if args_match:
            args_section = args_match.group(1)
            # Match parameter descriptions like "param_name (type): description"
            param_pattern = r'(\w+)\s*(?:\([^)]*\))?:\s*(.*?)(?=\n\s*\w+\s*(?:\([^)]*\))?:|\Z)'
            matches = re.findall(param_pattern, args_section, re.DOTALL)
            for param_name, desc in matches:
                # Clean up the description
                clean_desc = re.sub(r'\s+', ' ', desc.strip())
                param_descriptions[param_name] = clean_desc
    
    # Get function signature
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)
    
    # Build parameters schema
    properties = {}
    required_params = []
    
    for param_name, param in sig.parameters.items():
        # Determine parameter type
        param_type = "string"  # default
        items_type = "string"  # default for array items
        is_array = False
        
        if param_name in type_hints:
            hint = type_hints[param_name]
            
            # Handle Optional[T] by unwrapping
            origin = getattr(hint, '__origin__', None)
            args = getattr(hint, '__args__', ())
            
            # Unwrap Optional (Union with None)
            if origin is Union and type(None) in args:
                # Get the non-None type
                non_none_args = [a for a in args if a is not type(None)]
                if len(non_none_args) == 1:
                    hint = non_none_args[0]
                    origin = getattr(hint, '__origin__', None)
                    args = getattr(hint, '__args__', ())
            
            # Handle List[T] or List
            if hint == List or origin is list:
                is_array = True
                if args:
                    item_hint = args[0]
                    if item_hint == int:
                        items_type = "integer"
                    elif item_hint == float:
                        items_type = "number"
                    elif item_hint == bool:
                        items_type = "boolean"
                    else:
                        items_type = "string"
                else:
                    items_type = "string"
            elif hint == int:
                param_type = "integer"
            elif hint == float:
                param_type = "number"
            elif hint == bool:
                param_type = "boolean"
            # For other types, keep as string
        
        # Build property schema
        if is_array:
            prop_schema = {
                "type": "array",
                "items": {"type": items_type}
            }
        else:
            prop_schema = {"type": param_type}
        
        # Add description if available
        if param_name in param_descriptions:
            prop_schema["description"] = param_descriptions[param_name]
        
        properties[param_name] = prop_schema
        
        # Check if parameter is required
        if param.default == inspect.Parameter.empty:
            required_params.append(param_name)
    
    return {
        "type": "function",
        "function": {
            "name": func_name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required_params
            }
        }
    }


# Dynamically discover and load tools from configured toolsets
AVAILABLE_TOOLS = discover_toolsets(AUTOLOAD_TOOLSETS)


def add_toolset(toolset_name: str) -> bool:
    """
    Dynamically add a toolset to the available tools.
    
    Args:
        toolset_name: Name of the toolset to add (e.g., "gmail", "files", "system")
        
    Returns:
        bool: True if the toolset was added, False if already loaded or invalid
    """
    global AVAILABLE_TOOLS, _loaded_toolsets
    
    if toolset_name in _loaded_toolsets:
        return False
    
    _loaded_toolsets.add(toolset_name)
    
    # Discover and load tools from the new toolset
    new_tools = discover_toolsets([toolset_name])
    
    if new_tools:
        AVAILABLE_TOOLS.update(new_tools)
        return True
    
    return False


def get_all_tools() -> Dict[str, Callable]:
    """
    Get all available tools as a dictionary mapping names to functions.
    
    Returns:
        Dict[str, Callable]: Dictionary of tool names to functions
    """
    return AVAILABLE_TOOLS.copy()


def get_all_tool_schemas() -> List[Dict[str, Any]]:
    """
    Get all tool schemas in the format expected by OpenAI function calling.
    
    Returns:
        List[Dict[str, Any]]: List of tool schemas
    """
    return [get_function_schema(tool) for tool in AVAILABLE_TOOLS.values()]


def get_all_tool_permissions() -> Dict[str, str]:
    """
    Get permissions for all available tools.
    
    Returns:
        Dict[str, str]: Dictionary mapping tool names to their permission strings
    """
    return {name: getattr(tool, '_tool_permissions', "") for name, tool in AVAILABLE_TOOLS.items()}


def get_tool_by_name(name: str) -> Callable:
    """
    Get a specific tool by name.
    
    Args:
        name (str): Name of the tool
        
    Returns:
        Callable: The tool function
        
    Raises:
        KeyError: If tool with given name doesn't exist
    """
    if name not in AVAILABLE_TOOLS:
        raise KeyError(f"Tool '{name}' not found. Available tools: {list(AVAILABLE_TOOLS.keys())}")
    return AVAILABLE_TOOLS[name]


def get_tool_schema_by_name(name: str) -> Dict[str, Any]:
    """
    Get a specific tool schema by name.
    
    Args:
        name (str): Name of the tool
        
    Returns:
        Dict[str, Any]: The tool schema
        
    Raises:
        KeyError: If tool with given name doesn't exist
    """
    if name not in AVAILABLE_TOOLS:
        raise KeyError(f"Tool '{name}' not found. Available tools: {list(AVAILABLE_TOOLS.keys())}")
    return get_function_schema(AVAILABLE_TOOLS[name])


def get_tool_permissions(name: str) -> str:
    """
    Get the permissions required by a specific tool.
    
    Args:
        name (str): Name of the tool
        
    Returns:
        str: Permission string (e.g., "r", "rw", "rwx") or empty string if no permissions declared
        
    Raises:
        KeyError: If tool with given name doesn't exist
    """
    if name not in AVAILABLE_TOOLS:
        raise KeyError(f"Tool '{name}' not found. Available tools: {list(AVAILABLE_TOOLS.keys())}")
    return getattr(AVAILABLE_TOOLS[name], '_tool_permissions', "")


if __name__ == "__main__":
    # Example usage
    print("Available tools:")
    for name in AVAILABLE_TOOLS:
        print(f"  - {name}")
    
    print("\nTool schemas:")
    for schema in get_all_tool_schemas():
        print(f"  - {schema['function']['name']}: {schema['function']['description']}")