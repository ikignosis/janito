"""
Decorators for core tools registration.
"""

from typing import Type

# Registry for core tools
_core_tools_registry = []


def register_core_tool(cls: Type):
    """Decorator to register a core tool."""
    _core_tools_registry.append(cls)
    return cls


def get_core_tools():
    """Get all registered core tools."""
    return list(_core_tools_registry)
