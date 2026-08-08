"""
Main tools module for AI function calling.

This module provides easy access to all available tools and their schemas.

:class:`ToolsRegistry` groups the registry operations (lazy discovery,
toolset loading, skills enable/disable, lookups) behind a single class API;
the module-level functions below are thin delegators to a module-level
singleton (:data:`_registry`), so existing import sites keep working.

State location note
-------------------
The registry's state intentionally lives at **module level** (``AVAILABLE_TOOLS``,
``_tools_initialized``, ``_loaded_toolsets``, ``_skills_enabled``): tests
(``test_used_files.py``, ``test_tool_executor.py``) monkeypatch
``tools_registry.AVAILABLE_TOOLS`` and ``tools_registry._tools_initialized``
directly to inject stub tools without triggering the slow filesystem
discovery.  ``ToolsRegistry`` methods therefore read the module globals and
declare ``global`` only where they rebind a name (``_tools_initialized``,
``_skills_enabled``).
"""

import inspect
import re
from collections.abc import Callable
from typing import Any, Union, get_type_hints

from ..tools import discover_toolsets
from .skills_provider import get_skills_advertisement, get_skills_tools

# Configuration for auto-loading toolsets
AUTOLOAD_TOOLSETS = ["files", "system", "net", "codesearch"]

# Track loaded toolsets to avoid duplicates
_loaded_toolsets = set(AUTOLOAD_TOOLSETS.copy())

# Flag to enable skills support
_skills_enabled = True


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


# Lazily-initialized registry of available tools.
# Discovery is deferred until first access so that CLI flags (e.g. -r, -w, -x)
# can set running_privileges *before* tools are filtered.
AVAILABLE_TOOLS: dict[str, Callable] = {}
_tools_initialized: bool = False


class ToolsRegistry:
    """Grouped API over the module-level tools registry state.

    Encapsulates the registry operations: lazy discovery
    (:meth:`ensure_initialized`), dynamic toolset loading (:meth:`add_toolset`),
    skills enable/disable (:meth:`enable_skills` / :meth:`disable_skills`) and
    the tool lookups (:meth:`all_tools`, :meth:`get`, :meth:`permissions`, ...).

    The underlying state lives at module level (``AVAILABLE_TOOLS``,
    ``_tools_initialized``, ``_loaded_toolsets``, ``_skills_enabled``) so the
    test monkeypatches of ``tools_registry.AVAILABLE_TOOLS`` /
    ``_tools_initialized`` keep working; methods read the module globals and
    declare ``global`` only where they rebind a name.
    """

    def ensure_initialized(self) -> None:
        """
        Run tool discovery on first access (lazy initialization).

        This ensures ``running_privileges`` is already set by the time
        ``discover_toolsets`` applies its privilege-based filtering.
        """
        global _tools_initialized
        if _tools_initialized:
            return
        _tools_initialized = True

        AVAILABLE_TOOLS.update(discover_toolsets(AUTOLOAD_TOOLSETS))

        # Add skill tools if enabled
        if _skills_enabled:
            AVAILABLE_TOOLS.update(get_skills_tools())

    def add_toolset(self, toolset_name: str) -> bool:
        """
        Dynamically add a toolset to the available tools.

        Args:
            toolset_name: Name of the toolset to add (e.g., "gmail", "files", "system")

        Returns:
            bool: True if the toolset was added, False if already loaded or invalid
        """
        self.ensure_initialized()

        if toolset_name in _loaded_toolsets:
            return False

        _loaded_toolsets.add(toolset_name)

        # Discover and load tools from the new toolset
        new_tools = discover_toolsets([toolset_name])

        if new_tools:
            AVAILABLE_TOOLS.update(new_tools)
            return True

        return False

    def all_tools(self) -> dict[str, Callable]:
        """
        Get all available tools as a dictionary mapping names to functions.

        Returns:
            Dict[str, Callable]: Dictionary of tool names to functions
        """
        self.ensure_initialized()
        return AVAILABLE_TOOLS.copy()

    def all_schemas(self) -> list[dict[str, Any]]:
        """
        Get all tool schemas in the format expected by OpenAI function calling.

        Returns:
            List[Dict[str, Any]]: List of tool schemas
        """
        self.ensure_initialized()
        return [get_function_schema(tool) for tool in AVAILABLE_TOOLS.values()]

    def all_permissions(self) -> dict[str, str]:
        """
        Get permissions for all available tools.

        Returns:
            Dict[str, str]: Dictionary mapping tool names to their permission strings
        """
        self.ensure_initialized()
        return {
            name: getattr(tool, "_tool_permissions", "")
            for name, tool in AVAILABLE_TOOLS.items()
        }

    def get(self, name: str) -> Callable:
        """
        Get a specific tool by name.

        Args:
            name (str): Name of the tool

        Returns:
            Callable: The tool function

        Raises:
            KeyError: If tool with given name doesn't exist
        """
        self.ensure_initialized()
        if name not in AVAILABLE_TOOLS:
            raise KeyError(
                f"Tool '{name}' not found. Available tools: {list(AVAILABLE_TOOLS.keys())}"
            )
        return AVAILABLE_TOOLS[name]

    def schema(self, name: str) -> dict[str, Any]:
        """
        Get a specific tool schema by name.

        Args:
            name (str): Name of the tool

        Returns:
            Dict[str, Any]: The tool schema

        Raises:
            KeyError: If tool with given name doesn't exist
        """
        return get_function_schema(self.get(name))

    def permissions(self, name: str) -> str:
        """
        Get the permissions required by a specific tool.

        Args:
            name (str): Name of the tool

        Returns:
            str: Permission string (e.g., "r", "rw", "rwx") or empty string if no permissions declared

        Raises:
            KeyError: If tool with given name doesn't exist
        """
        self.ensure_initialized()
        if name not in AVAILABLE_TOOLS:
            raise KeyError(
                f"Tool '{name}' not found. Available tools: {list(AVAILABLE_TOOLS.keys())}"
            )
        return getattr(AVAILABLE_TOOLS[name], "_tool_permissions", "")

    def skills_section(self) -> str:
        """
        Get the skills advertisement section to append to system prompts.

        Returns:
            String with skill names, descriptions, and tool instructions
        """
        if not _skills_enabled:
            return ""

        advertisement = get_skills_advertisement()

        if not advertisement:
            return ""

        # Add tool usage instructions
        tools_section = """
\n## Skill Tools
Use these tools to load skill content when needed:
- **load_skill(skill_name)**: Load the full instructions from a skill's SKILL.md file
- **read_skill_resource(skill_name, resource_name)**: Read a supplementary file from a skill

You should load a skill when the user's request matches its description or you need specialized guidance."""

        return advertisement + tools_section

    def enable_skills(self) -> None:
        """Enable skills support."""
        global _skills_enabled
        self.ensure_initialized()
        _skills_enabled = True
        AVAILABLE_TOOLS.update(get_skills_tools())

    def disable_skills(self) -> None:
        """Disable skills support."""
        global _skills_enabled
        self.ensure_initialized()
        _skills_enabled = False
        for tool_name in ["load_skill", "read_skill_resource"]:
            AVAILABLE_TOOLS.pop(tool_name, None)


# Module-level singleton backing the functions below.
_registry = ToolsRegistry()


def _ensure_initialized() -> None:
    """
    Run tool discovery on first access (lazy initialization).

    This ensures ``running_privileges`` is already set by the time
    ``discover_toolsets`` applies its privilege-based filtering.
    """
    _registry.ensure_initialized()


def add_toolset(toolset_name: str) -> bool:
    """
    Dynamically add a toolset to the available tools.

    Args:
        toolset_name: Name of the toolset to add (e.g., "gmail", "files", "system")

    Returns:
        bool: True if the toolset was added, False if already loaded or invalid
    """
    return _registry.add_toolset(toolset_name)


def get_all_tools() -> dict[str, Callable]:
    """
    Get all available tools as a dictionary mapping names to functions.

    Returns:
        Dict[str, Callable]: Dictionary of tool names to functions
    """
    return _registry.all_tools()


def get_all_tool_schemas() -> list[dict[str, Any]]:
    """
    Get all tool schemas in the format expected by OpenAI function calling.

    Returns:
        List[Dict[str, Any]]: List of tool schemas
    """
    return _registry.all_schemas()


def get_all_tool_permissions() -> dict[str, str]:
    """
    Get permissions for all available tools.

    Returns:
        Dict[str, str]: Dictionary mapping tool names to their permission strings
    """
    return _registry.all_permissions()


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
    return _registry.get(name)


def get_tool_schema_by_name(name: str) -> dict[str, Any]:
    """
    Get a specific tool schema by name.

    Args:
        name (str): Name of the tool

    Returns:
        Dict[str, Any]: The tool schema

    Raises:
        KeyError: If tool with given name doesn't exist
    """
    return _registry.schema(name)


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
    return _registry.permissions(name)


def get_skills_section() -> str:
    """
    Get the skills advertisement section to append to system prompts.

    Returns:
        String with skill names, descriptions, and tool instructions
    """
    return _registry.skills_section()


def enable_skills() -> None:
    """Enable skills support."""
    _registry.enable_skills()


def disable_skills() -> None:
    """Disable skills support."""
    _registry.disable_skills()


if __name__ == "__main__":
    # Example usage
    print("Available tools:")
    for name in AVAILABLE_TOOLS:
        print(f"  - {name}")

    print("\nTool schemas:")
    for schema in get_all_tool_schemas():
        print(f"  - {schema['function']['name']}: {schema['function']['description']}")
