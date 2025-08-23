from janito.tools.adapters.local import LocalToolsAdapter
from janito.tools.adapters.local.adapter import (
    LocalToolsAdapter as _internal_local_tools_adapter,
)


def get_local_tools_adapter(workdir=None, allowed_permissions=None):
    # Use set_verbose_tools on the returned adapter to set verbosity as needed
    import os

    if workdir is not None and not os.path.exists(workdir):
        os.makedirs(workdir, exist_ok=True)
    # Permissions are now managed globally; ignore allowed_permissions argument except for backward compatibility
    # Create and initialize adapter
    from janito.tools.initialize import initialize_tools

    registry = initialize_tools(LocalToolsAdapter(workdir=workdir))
    # Change workdir if requested
    if workdir is not None:
        try:
            import os

            if not os.path.exists(workdir):
                os.makedirs(workdir, exist_ok=True)
            os.chdir(workdir)
            registry.workdir = workdir
        except Exception:
            pass
    return registry


# Initialize the global adapter - defer import to avoid circular dependencies
local_tools_adapter = None


def get_local_tools_adapter(workdir=None, allowed_permissions=None):
    """Get the global tools adapter, initializing on first use."""
    global local_tools_adapter
    if local_tools_adapter is None:
        from janito.tools.initialize import initialize_tools

        adapter = LocalToolsAdapter(workdir=workdir)
        local_tools_adapter = initialize_tools(adapter)

    # Handle workdir if provided
    if workdir is not None and local_tools_adapter is not None:
        import os

        if not os.path.exists(workdir):
            os.makedirs(workdir, exist_ok=True)
        os.chdir(workdir)
        local_tools_adapter.workdir = workdir

    return local_tools_adapter


__all__ = [
    "LocalToolsAdapter",
    "get_local_tools_adapter",
]
