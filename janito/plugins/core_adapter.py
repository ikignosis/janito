"""
Core plugin adapter for legacy plugin system.

This module provides proper Plugin class implementations for core plugins
that use the function-based approach instead of class-based.
"""

from janito.plugin_system.base import Plugin, PluginMetadata
from typing import List, Type
from janito.tools.tool_base import ToolBase, ToolPermissions


class CorePluginAdapter(Plugin):
    """Adapter for core plugins using function-based tools."""

    def __init__(self, plugin_name: str, description: str, tools_module):
        super().__init__()
        self._plugin_name = plugin_name
        self._description = description
        self._tools_module = tools_module
        self._tool_classes = []

        # Set the metadata attribute that Plugin expects
        self.metadata = self.get_metadata()

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
        """Initialize the plugin by creating tool classes."""
        # Get tools from the module
        tools = getattr(self._tools_module, "__plugin_tools__", [])

        self._tool_classes = []
        for tool_func in tools:
            if callable(tool_func):
                tool_class = self._create_tool_class(tool_func)
                self._tool_classes.append(tool_class)


def create_core_plugin(
    plugin_name: str, description: str, tools_module
) -> CorePluginAdapter:
    """Create a core plugin adapter."""
    return CorePluginAdapter(plugin_name, description, tools_module)
