"""
Generate OpenAI-compatible tool schemas for Z.AI API.
"""

import inspect
from typing import get_type_hints, Dict, Any, Optional, List, Union
from janito.tooling.tool_base import ToolBase


def generate_tool_schemas(tool_classes):
    """
    Generate OpenAI-compatible tool schemas from tool classes.

    Args:
        tool_classes: List of Tool classes to generate schemas for

    Returns:
        List of OpenAI-compatible tool schemas
    """
    schemas = []
    for tool_class in tool_classes:
        schema = generate_tool_schema(tool_class)
        if schema:
            schemas.append(schema)
    return schemas


def generate_tool_schema(tool_class):
    """
    Generate an OpenAI-compatible tool schema from a Tool class.

    Args:
        tool_class: Tool class to generate schema for

    Returns:
        OpenAI-compatible tool schema dict
    """
    if not issubclass(tool_class, ToolBase):
        return None

    tool_instance = tool_class()

    # Get the execute or run method
    execute_method = getattr(tool_class, "execute", None)
    if execute_method is None:
        execute_method = getattr(tool_class, "run", None)
    if execute_method is None:
        return None

    # Get method signature and type hints
    try:
        sig = inspect.signature(execute_method)
        type_hints = get_type_hints(execute_method)
    except (ValueError, TypeError):
        return None

    # Build parameters schema
    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        param_type = type_hints.get(param_name, str)
        param_schema = python_type_to_json_schema(param_type)

        # Add description if available
        if hasattr(tool_instance, "get_parameter_description"):
            desc = tool_instance.get_parameter_description(param_name)
            if desc:
                param_schema["description"] = desc

        properties[param_name] = param_schema

        # Check if required
        if param.default == inspect.Parameter.empty:
            required.append(param_name)

    schema = {
        "type": "function",
        "function": {
            "name": getattr(tool_instance, "tool_name", tool_class.__name__),
            "description": getattr(
                tool_instance, "description", f"Execute {tool_class.__name__}"
            ),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }

    return schema


def python_type_to_json_schema(python_type):
    """
    Convert Python type hints to JSON schema types.

    Args:
        python_type: Python type hint

    Returns:
        JSON schema dict
    """
    if python_type == str:
        return {"type": "string"}
    elif python_type == int:
        return {"type": "integer"}
    elif python_type == float:
        return {"type": "number"}
    elif python_type == bool:
        return {"type": "boolean"}
    elif hasattr(python_type, "__origin__"):
        # Handle generic types
        origin = python_type.__origin__
        if origin == list or origin == List:
            args = getattr(python_type, "__args__", (str,))
            item_type = args[0] if args else str
            return {"type": "array", "items": python_type_to_json_schema(item_type)}
        elif origin == dict or origin == Dict:
            return {"type": "object"}
        elif origin == Union:
            args = getattr(python_type, "__args__", ())
            # Handle Optional types (Union with None)
            if len(args) == 2 and type(None) in args:
                non_none_type = args[0] if args[1] is type(None) else args[1]
                schema = python_type_to_json_schema(non_none_type)
                return schema

    # Default fallback
    return {"type": "string"}
