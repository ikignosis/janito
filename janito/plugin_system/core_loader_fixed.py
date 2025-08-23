"""
Fixed core plugin loader.

This module provides a working implementation to load core plugins
by directly using the Plugin base class properly.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Optional, List, Type

from janito.plugin_system.base import Plugin, PluginMetadata
from janito.tools.tool_base import ToolBase, ToolPermissions


class CorePlugin(Plugin):
    """Working core plugin implementation."""

    def __init__(self, name: str, description: str, tools: list):
        self._plugin_name = name
        self._description = description
        self._tools = tools
        self._tool_classes = []
        super().__init__()  # Call super after setting attributes

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self._plugin_name,
            version="1.0.0",
            description=self._description,
            author="Janito",
            license="MIT",
        )

    def get_tools(self) -> List[Type[ToolBase]]:
        return self._tool_classes

    def _create_tool_class(self, func):
        """Create a ToolBase class from a function."""
        resolved_tool_name = getattr(func, "tool_name", func.__name__)
        
        # Create a proper tool class with explicit parameters and documentation
        import inspect
        from typing import get_type_hints
        
        func_sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        
        # Build parameter definitions for the run method
        param_defs = []
        param_docs = []
        for name, param in func_sig.parameters.items():
            type_hint = type_hints.get(name, str)
            if param.default == inspect.Parameter.empty:
                param_defs.append(f"{name}: {type_hint.__name__}")
            else:
                param_defs.append(f"{name}: {type_hint.__name__} = {repr(param.default)}")
            
            # Add parameter documentation
            param_docs.append(f"    {name}: {type_hint.__name__} - Parameter {name}")
        
        # Get function docstring or create one
        func_doc = func.__doc__ or f"Execute {resolved_tool_name} tool"
        
        # Create the tool class with proper signature and documentation
        exec_globals = {
            'ToolBase': ToolBase,
            'ToolPermissions': ToolPermissions,
            'func': func,
            'inspect': inspect,
            'str': str,
            'List': list,
            'Dict': dict,
            'Optional': type(None),
        }
        
        param_docs_str = '\n'.join(param_docs)
        
        class_def = f'''
class DynamicTool(ToolBase):
    """
    {func_doc}
    
    Parameters:
{param_docs_str}
    
    Returns:
        str: Execution result
    """
    tool_name = "{resolved_tool_name}"
    permissions = ToolPermissions(read=True, write=True, execute=True)
    
    def __init__(self):
        super().__init__()
    
    def run(self, {', '.join(param_defs)}) -> str:
        kwargs = locals()
        sig = inspect.signature(func)
        
        # Filter kwargs to only include parameters the function accepts
        filtered_kwargs = {{}}
        for name, param in sig.parameters.items():
            if name in kwargs and kwargs[name] is not None:
                filtered_kwargs[name] = kwargs[name]
        
        result = func(**filtered_kwargs)
        return str(result) if result is not None else ""
'''
        
        exec(class_def, exec_globals)
        return exec_globals['DynamicTool']
        
        return DynamicTool

    def initialize(self):
        """Initialize by creating tool classes."""
        self._tool_classes = []
        for tool_func in self._tools:
            if callable(tool_func):
                tool_class = self._create_tool_class(tool_func)
                self._tool_classes.append(tool_class)


def load_core_plugin(plugin_name: str) -> Optional[Plugin]:
    """
    Load a core plugin by name.

    Args:
        plugin_name: Name of the plugin (e.g., 'core.filemanager')

    Returns:
        Plugin instance if loaded successfully
    """
    try:
        # Parse plugin name
        if "." not in plugin_name:
            return None

        parts = plugin_name.split(".")
        if len(parts) != 2:
            return None

        package_name, submodule_name = parts

        # Handle imagedisplay specially
        if plugin_name == "core.imagedisplay":
            # Import the actual plugin class
            try:
                from janito.plugins.core.imagedisplay.plugin import ImageDisplayPlugin

                return ImageDisplayPlugin()
            except ImportError as e:
                print(f"Failed to load imagedisplay: {e}")
                return None

        # Build path to plugin
        plugin_path = (
            Path("janito/plugins") / package_name / submodule_name / "__init__.py"
        )
        if not plugin_path.exists():
            return None

        # Load the module
        spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)

        # Add module to sys.modules to prevent circular imports
        sys.modules[plugin_name] = module

        try:
            # Read and execute the module content
            with open(plugin_path, "r", encoding="utf-8") as f:
                code = f.read()

            # Execute in module's namespace
            exec(code, module.__dict__)

            # Get plugin info
            name = module.__dict__.get("__plugin_name__", plugin_name)
            description = module.__dict__.get(
                "__plugin_description__", f"Core plugin: {plugin_name}"
            )
            tools = module.__dict__.get("__plugin_tools__", [])

            if not tools:
                return None

            # Ensure all tools have tool_name attribute
            for tool in tools:
                if tool is not None and not hasattr(tool, "tool_name"):
                    tool.tool_name = tool.__name__

            # Create plugin
            plugin = CorePlugin(name, description, tools)
            plugin.initialize()
            return plugin
        finally:
            # Clean up sys.modules
            if plugin_name in sys.modules:
                del sys.modules[plugin_name]

    except Exception as e:
        print(f"Error loading core plugin {plugin_name}: {e}")
        return None


def get_core_plugins() -> list:
    """Get list of all available core plugins."""
    core_plugins = [
        "core.filemanager",
        "core.codeanalyzer",
        "core.system",
        "core.imagedisplay",
        "dev.pythondev",
        "dev.visualization",
        "ui.userinterface",
        "web.webtools",
    ]

    # All core plugins are always available
    return core_plugins
