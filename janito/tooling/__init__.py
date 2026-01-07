from janito.plugins.tools.local import (
    local_tools_adapter as _internal_local_tools_adapter,
    LocalToolsAdapter,
)


def get_local_tools_adapter(workdir=None, allowed_permissions=None):
    # Use set_verbose_tools on the returned adapter to set verbosity as needed
    import os

    if workdir is not None and not os.path.exists(workdir):
        os.makedirs(workdir, exist_ok=True)
    # Permissions are now managed globally; ignore allowed_permissions argument except for backward compatibility
    # Reuse the singleton adapter defined in janito.plugins.tools.local to maintain tool registrations
    registry = _internal_local_tools_adapter
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


local_tools_adapter = _internal_local_tools_adapter

__all__ = [
    "LocalToolsAdapter",
    "get_local_tools_adapter",
    "local_tools_adapter",
]
