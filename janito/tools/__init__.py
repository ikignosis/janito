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


# Tools that were skipped during discovery because their should_load()
# validation failed, mapped to a human-readable reason.
_skipped_tools: Dict[str, str] = {}


def get_skipped_tools() -> Dict[str, str]:
    """
    Get tools that were skipped during discovery.

    Returns:
        Dict[str, str]: Mapping of tool class names to skip reasons
    """
    return _skipped_tools.copy()


def _check_should_load(cls: type) -> bool:
    """
    Run a tool class's should_load() validation.

    Tools that fail validation (or raise during validation) are recorded
    in _skipped_tools and excluded from discovery.

    Args:
        cls: The tool class to validate

    Returns:
        bool: True if the tool should be loaded, False to skip it
    """
    should_load = getattr(cls, "should_load", None)
    if not callable(should_load):
        return True
    try:
        if should_load():
            return True
        reason = getattr(cls, "_load_skip_reason", "") or "should_load() returned False"
        _skipped_tools[cls.__name__] = reason
    except Exception as e:
        _skipped_tools[cls.__name__] = f"should_load() raised {type(e).__name__}: {e}"
    return False


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
                                # Let tools opt out of loading (missing binaries,
                                # unsupported platform, missing credentials, ...)
                                if not _check_should_load(attr):
                                    continue

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
                                    # Propagate the load validation hook for later introspection
                                    class_tool_wrapper.should_load = getattr(cls, 'should_load', None)
                                    
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
