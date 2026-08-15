"""
Shared tool-filtering helpers for the /read and /write shell commands.

Both commands send the prompt through the shell's main-prompt path while
restricting ``tools=`` to a permission subset of the built-in tools: /read
offers the read-only (``"r"``) tools, /write offers the write-only (``"w"``)
tools. The filtering itself is identical, so it lives here.
"""

from typing import Any


def get_tool_schemas_by_permission(permission: str) -> list[dict[str, Any]]:
    """Return the function-calling schemas of the tools whose declared
    permission is exactly ``permission``.

    A tool matches when its ``_tool_permissions`` equals ``permission`` (the
    value set by ``@tool(permissions=...)``): e.g. ``"r"`` for read-only and
    ``"w"`` for write-only tools. Tools declaring no permissions (e.g. the
    skill tools), tools combining permissions (``"rw"``, ``"rwx"``, ...) and
    MCP tools (which carry no permission metadata here) are excluded -- only
    the matching built-in tools are offered.
    """
    from janito.tooling.tools_registry import (
        get_all_tool_permissions,
        get_all_tool_schemas,
    )

    matching_names = {
        name
        for name, permissions in get_all_tool_permissions().items()
        if permissions == permission
    }
    return [
        schema
        for schema in get_all_tool_schemas()
        if schema.get("function", {}).get("name") in matching_names
    ]
