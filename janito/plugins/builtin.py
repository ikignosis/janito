"""
Builtin plugin system for janito-packaged plugins.

This module provides the infrastructure for plugins that are bundled
with janito and available by default without requiring external installation.
"""

import importlib
from typing import Dict, List, Optional, Type
from janito.plugin_system.base import Plugin


class BuiltinPluginRegistry:
    """Registry for builtin plugins that come packaged with janito."""

    _plugins: Dict[str, Type[Plugin]] = {}

    @classmethod
    def register(cls, name: str, plugin_class: Type[Plugin]) -> None:
        """Register a builtin plugin."""
        cls._plugins[name] = plugin_class

    @classmethod
    def get_plugin_class(cls, name: str) -> Optional[Type[Plugin]]:
        """Get the plugin class for a builtin plugin."""
        return cls._plugins.get(name)

    @classmethod
    def list_builtin_plugins(cls) -> List[str]:
        """List all registered builtin plugins."""
        return list(cls._plugins.keys())

    @classmethod
    def is_builtin(cls, name: str) -> bool:
        """Check if a plugin is builtin."""
        return name in cls._plugins


def register_builtin_plugin(name: str):
    """Decorator to register a plugin as builtin."""

    def decorator(plugin_class: Type[Plugin]) -> Type[Plugin]:
        BuiltinPluginRegistry.register(name, plugin_class)
        return plugin_class

    return decorator


def load_builtin_plugin(name: str) -> Optional[Plugin]:
    """Load a builtin plugin by name."""
    plugin_class = BuiltinPluginRegistry.get_plugin_class(name)
    if plugin_class:
        return plugin_class()
    return None


# Auto-register janito-coder plugins as builtin
try:
    from janito_coder.plugins import (
        GitAnalyzerPlugin,
        CodeNavigatorPlugin,
        DependencyAnalyzerPlugin,
        CodeFormatterPlugin,
        TestRunnerPlugin,
        LinterPlugin,
        DebuggerPlugin,
        PerformanceProfilerPlugin,
        SecurityScannerPlugin,
        DocumentationGeneratorPlugin,
    )

    # Register all janito-coder plugins as builtin
    BuiltinPluginRegistry.register("git_analyzer", GitAnalyzerPlugin)
    BuiltinPluginRegistry.register("code_navigator", CodeNavigatorPlugin)
    BuiltinPluginRegistry.register("dependency_analyzer", DependencyAnalyzerPlugin)
    BuiltinPluginRegistry.register("code_formatter", CodeFormatterPlugin)
    BuiltinPluginRegistry.register("test_runner", TestRunnerPlugin)
    BuiltinPluginRegistry.register("linter", LinterPlugin)
    BuiltinPluginRegistry.register("debugger", DebuggerPlugin)
    BuiltinPluginRegistry.register("performance_profiler", PerformanceProfilerPlugin)
    BuiltinPluginRegistry.register("security_scanner", SecurityScannerPlugin)
    BuiltinPluginRegistry.register(
        "documentation_generator", DocumentationGeneratorPlugin
    )

    # Register core tools plugin
    from janito.plugins.tools import CoreToolsPlugin

    BuiltinPluginRegistry.register("core_tools", CoreToolsPlugin)

except ImportError:
    # janito-coder not available, skip registration
    pass

# Register core tools plugin (always available)
try:
    from janito.plugins.tools import CoreToolsPlugin

    BuiltinPluginRegistry.register("core_tools", CoreToolsPlugin)
except ImportError:
    # Should not happen, but handle gracefully
    pass
