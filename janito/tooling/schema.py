"""
Function-schema generation.

Builds OpenAI-compatible function-calling schemas from a callable's type
hints and docstring.  Extracted from :mod:`janito.tooling.tools_registry`
so the registry module stays
focused on discovery, toolset management and lookups.
"""

import inspect
import re
from collections.abc import Callable
from typing import Any, Union, get_type_hints


def _parse_docstring(docstring: str, func_name: str):
    """Extract the main description and per-parameter descriptions."""
    description = docstring.split("\n")[0] if docstring else f"Function {func_name}"

    param_descriptions = {}
    if docstring:
        # Look for Args section in docstring
        args_match = re.search(
            r"Args:\s*(.*?)(?:\n\s*\w+:|\Z)", docstring, re.DOTALL | re.IGNORECASE
        )
        if args_match:
            args_section = args_match.group(1)
            # Match parameter descriptions like "param_name (type): description"
            param_pattern = (
                r"(\w+)\s*(?:\([^)]*\))?:\s*(.*?)(?=\n\s*\w+\s*(?:\([^)]*\))?:|\Z)"
            )
            matches = re.findall(param_pattern, args_section, re.DOTALL)
            for param_name, desc in matches:
                # Clean up the description
                clean_desc = re.sub(r"\s+", " ", desc.strip())
                param_descriptions[param_name] = clean_desc

    return description, param_descriptions


def _resolve_array_items_type(args: tuple) -> str:
    """Map the first list item hint to a JSON schema type."""
    if not args:
        return "string"
    item_hint = args[0]
    if item_hint is int:
        return "integer"
    if item_hint is float:
        return "number"
    if item_hint is bool:
        return "boolean"
    return "string"


def _resolve_type_info(hint):
    """Map a type hint to ``(param_type, items_type, is_array)``."""
    param_type = "string"  # default
    items_type = "string"  # default for array items
    is_array = False

    origin = getattr(hint, "__origin__", None)
    args = getattr(hint, "__args__", ())

    # Unwrap Optional (Union with None)
    if origin is Union and type(None) in args:
        # Get the non-None type
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            hint = non_none_args[0]
            origin = getattr(hint, "__origin__", None)
            args = getattr(hint, "__args__", ())

    # Handle List[T] or List
    if hint is list or origin is list:
        is_array = True
        items_type = _resolve_array_items_type(args)
    elif hint is int:
        param_type = "integer"
    elif hint is float:
        param_type = "number"
    elif hint is bool:
        param_type = "boolean"
    # For other types, keep as string

    return param_type, items_type, is_array


def get_function_schema(func: Callable) -> dict[str, Any]:
    """
    Generate a JSON schema for a function based on its signature and docstring.

    Args:
        func (Callable): The function to generate a schema for

    Returns:
        Dict[str, Any]: OpenAI function calling schema
    """
    # Get function name
    func_name = func.__name__

    # Get function docstring and parse it
    docstring = inspect.getdoc(func) or ""
    description, param_descriptions = _parse_docstring(docstring, func_name)

    # Get function signature
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    # Build parameters schema
    properties = {}
    required_params = []

    for param_name, param in sig.parameters.items():
        # Determine parameter type
        hint = type_hints.get(param_name)
        if hint:
            param_type, items_type, is_array = _resolve_type_info(hint)
        else:
            param_type, items_type, is_array = "string", "string", False

        # Build property schema
        if is_array:
            prop_schema = {"type": "array", "items": {"type": items_type}}
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
                "required": required_params,
            },
        },
    }
