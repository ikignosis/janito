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
``_tools_initialized``, ``_loaded_toolsets``, ``_skills_enabled``,
``_tools_loading_enabled``): tests
(``test_used_files.py``, ``test_tool_executor.py``) monkeypatch
``tools_registry.AVAILABLE_TOOLS`` and ``tools_registry._tools_initialized``
directly to inject stub tools without triggering the slow filesystem
discovery.  ``ToolsRegistry`` methods therefore read the module globals and
declare ``global`` only where they rebind a name (``_tools_initialized``,
``_skills_enabled``, ``_tools_loading_enabled``).
"""

from collections.abc import Callable
from typing import Any

from ..tools import discover_toolsets
from .schema import get_function_schema
from .skills_provider import get_skills_advertisement, get_skills_tools

# Configuration for auto-loading toolsets
AUTOLOAD_TOOLSETS = ["files", "system", "net"]

# Track loaded toolsets to avoid duplicates
_loaded_toolsets = set(AUTOLOAD_TOOLSETS.copy())

# Flag to enable skills support
_skills_enabled = True

# Whether non-skill tools (the autoload toolsets and any toolset added via
# ``add_toolset``, e.g. gmail/onedrive/janitoweb) are loaded at all.
# ``--no-tools`` sets this to False; skill tools are never affected, so they
# stay available even when every other tool is disabled.
_tools_loading_enabled = True


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
    ``_tools_initialized``, ``_loaded_toolsets``, ``_skills_enabled``,
    ``_tools_loading_enabled``) so the
    test monkeypatches of ``tools_registry.AVAILABLE_TOOLS`` /
    ``_tools_initialized`` keep working; methods read the module globals and
    declare ``global`` only where they rebind a name.
    """

    def ensure_initialized(self) -> None:
        """
        Run tool discovery on first access (lazy initialization).

        This ensures ``running_privileges`` is already set by the time
        ``discover_toolsets`` applies its privilege-based filtering.

        When tool loading is disabled (``--no-tools``), the autoload
        toolsets are skipped but the skill tools are still registered, so
        ``load_skill`` / ``read_skill_resource`` stay available.
        """
        global _tools_initialized
        if _tools_initialized:
            return
        _tools_initialized = True

        if _tools_loading_enabled:
            AVAILABLE_TOOLS.update(discover_toolsets(AUTOLOAD_TOOLSETS))

        # Add skill tools if enabled. Never gated by _tools_loading_enabled:
        # --no-tools disables the other tools but leaves skills enabled.
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
        # --no-tools: no toolset is loaded (skill tools stay available).
        if not _tools_loading_enabled:
            return False

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

    def register_plugin_tools(self, tools: dict[str, Callable]) -> None:
        """
        Register tools contributed by a plugin.

        Plugin tools go through the same ``should_load()`` / privilege
        gating as built-in tools (applied by ``wrap_tool_class`` /
        ``discover_module_tools`` in the plugin manager), so only surviving
        callables should be passed here.  Plugin tools are **not** gated by
        ``_tools_loading_enabled`` (``--no-tools``): plugins are disabled
        independently via ``--no-plugins``.

        Args:
            tools: Mapping of tool names to wrapped callables.
        """
        if not tools:
            return
        self.ensure_initialized()
        AVAILABLE_TOOLS.update(tools)

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

    def disable_tools_loading(self) -> None:
        """Disable loading of non-skill tools (``--no-tools``).

        Must be called before the first :meth:`ensure_initialized` to take
        effect: afterwards the autoload toolsets are never discovered and
        :meth:`add_toolset` becomes a no-op.  Skill tools are not affected.
        """
        global _tools_loading_enabled
        _tools_loading_enabled = False

    def tools_loading_enabled(self) -> bool:
        """Whether non-skill tools are loaded (False after ``--no-tools``)."""
        return _tools_loading_enabled


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


def disable_tools_loading() -> None:
    """Disable loading of non-skill tools (``--no-tools``).

    Skill tools (``load_skill`` / ``read_skill_resource``) stay enabled.
    """
    _registry.disable_tools_loading()


def register_plugin_tools(tools: dict[str, Callable]) -> None:
    """
    Register tools contributed by a plugin.

    Args:
        tools: Mapping of tool names to wrapped callables (see
            :meth:`ToolsRegistry.register_plugin_tools`).
    """
    _registry.register_plugin_tools(tools)


def tools_loading_enabled() -> bool:
    """Whether non-skill tools are loaded (False after ``--no-tools``)."""
    return _registry.tools_loading_enabled()


if __name__ == "__main__":
    # Example usage
    print("Available tools:")
    for name in AVAILABLE_TOOLS:
        print(f"  - {name}")

    print("\nTool schemas:")
    for schema in get_all_tool_schemas():
        print(f"  - {schema['function']['name']}: {schema['function']['description']}")
