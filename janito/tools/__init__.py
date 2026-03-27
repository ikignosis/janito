"""
Main tools package with auto-discovery support.

This package provides infrastructure for discovering and loading toolsets
dynamically based on the AUTOLOAD_TOOLSETS configuration.
"""

import os
import importlib
import inspect
from typing import Dict, Callable, List, get_type_hints


from .decorator import is_tool


def discover_toolsets(toolset_names: List[str]) -> Dict[str, Callable]:
    """
    Discover and load tools from specified toolsets.
    
    Args:
        toolset_names: List of toolset names to load (e.g., ["files", "git"])
        
    Returns:
        Dict[str, Callable]: Dictionary mapping tool names to functions
    """
    tools = {}
    tools_dir = os.path.dirname(__file__)
    
    for toolset_name in toolset_names:
        toolset_path = os.path.join(tools_dir, toolset_name)
        if not os.path.exists(toolset_path):
            continue
            
        # Look for Python files in the toolset directory (excluding __init__.py)
        for filename in os.listdir(toolset_path):
            if filename.endswith('.py') and filename != '__init__.py':
                module_name = filename[:-3]  # Remove .py extension
                try:
                    # Import the module
                    full_module_name = f'janito.tools.{toolset_name}.{module_name}'
                    module = importlib.import_module(full_module_name)
                    
                    # Get all attributes that are classes defined in this module
                    for attr_name in dir(module):
                        if attr_name.startswith('_'):
                            continue
                            
                        attr = getattr(module, attr_name)
                        if not isinstance(attr, type):
                            continue
                            
                        # Check if the class is actually defined in this module
                        # (not imported from elsewhere)
                        if hasattr(attr, '__module__') and attr.__module__ == full_module_name:
                            # Check if the class is explicitly marked as a tool
                            if is_tool(attr):
                                # Create a wrapper function that instantiates and calls run
                                def make_class_tool(cls):
                                    # Get the run method signature and type hints
                                    run_method = getattr(cls, 'run')
                                    run_sig = inspect.signature(run_method)
                                    run_type_hints = get_type_hints(run_method)
                                    
                                    # Create a wrapper with the same signature as the run method
                                    # but without the 'self' parameter
                                    params = list(run_sig.parameters.values())[1:]  # Skip 'self'
                                    new_sig = run_sig.replace(parameters=params)
                                    
                                    def class_tool_wrapper(*args, **kwargs):
                                        instance = cls()
                                        return instance.run(*args, **kwargs)
                                    
                                    # Set the correct signature and metadata
                                    class_tool_wrapper.__signature__ = new_sig
                                    class_tool_wrapper.__name__ = cls.__name__
                                    class_tool_wrapper.__doc__ = cls.__doc__
                                    class_tool_wrapper._is_tool = True
                                    class_tool_wrapper._tool_permissions = getattr(cls, '_tool_permissions', "")
                                    
                                    # Preserve type hints (excluding 'self')
                                    class_tool_wrapper.__annotations__ = {
                                        k: v for k, v in run_type_hints.items() if k != 'self'
                                    }
                                    
                                    return class_tool_wrapper
                                
                                tools[attr_name] = make_class_tool(attr)
                                    
                except Exception as e:
                    # Silently skip modules that can't be imported
                    # In a real system, you might want to log this
                    continue
    
    return tools
