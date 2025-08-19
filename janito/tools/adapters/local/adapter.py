from typing import Type, Dict, Any
from janito.tools.tools_adapter import ToolsAdapterBase as ToolsAdapter
from janito.tools.tool_use_tracker import ToolUseTracker


class LocalToolsAdapter(ToolsAdapter):
    """Local, in-process implementation of :class:`ToolsAdapterBase`.

    This adapter keeps an **in-memory registry** of tool classes and manages
    permission filtering (read/write/execute) as required by the janito CLI.

    The legacy ``set_execution_tools_enabled()`` helper has been removed – use
    ``janito.tools.permissions.set_global_allowed_permissions`` or
    :py:meth:`LocalToolsAdapter.set_allowed_permissions` to adjust the
    permission mask at runtime.

    Apart from registration/lookup helpers the class derives all execution
    logic from :class:`janito.tools.tools_adapter.ToolsAdapterBase`.
    """

    def __init__(self, tools=None, event_bus=None, workdir=None):
        """Create a new LocalToolsAdapter.

        Parameters
        ----------
        tools : list, optional
            An optional iterable with tool *classes* (not instances) that should
            be registered immediately.
        event_bus : janito.event_bus.bus.EventBus, optional
            The event bus to which tool-related events will be published.  When
            *None* (default) the **global** :pydata:`janito.event_bus.bus.event_bus`
            singleton is used so that CLI components such as the
            :class:`janito.cli.rich_terminal_reporter.RichTerminalReporter` will
            receive security violation or execution events automatically.
        workdir : str | pathlib.Path, optional
            Base directory that path-security checks will allow.  Defaults to
            the current working directory at the time of instantiation.
        """
        # Fall back to the global event bus so that ReportEvents emitted from
        # the tools adapter (for example path-security violations) are visible
        # to UI components even if the caller did not supply a custom bus.
        if event_bus is None:
            from janito.event_bus.bus import event_bus as global_event_bus

            event_bus = global_event_bus

        super().__init__(tools=tools, event_bus=event_bus)

        # Internal registry structure: { tool_name: {"class": cls, "instance": obj, "function": obj.run} }
        self._tools: Dict[str, Dict[str, Any]] = {}

        import os

        self.workdir = workdir or os.getcwd()
        # Ensure *some* workdir is set – fallback to CWD.
        if not self.workdir:
            self.workdir = os.getcwd()
        # Normalise by changing the actual process working directory for
        # consistency with many file-system tools.
        os.chdir(self.workdir)

        # Initialize tool tracker
        self.tool_tracker = ToolUseTracker.instance()

        if tools:
            for tool in tools:
                self.register_tool(tool)

    # ---------------------------------------------------------------------
    # Registration helpers
    # ---------------------------------------------------------------------
    def register_tool(self, tool_class: Type):
        instance = tool_class()
        if not hasattr(instance, "run") or not callable(instance.run):
            raise TypeError(
                f"Tool '{tool_class.__name__}' must implement a callable 'run' method."
            )
        tool_name = getattr(instance, "tool_name", None)
        if not tool_name or not isinstance(tool_name, str):
            raise ValueError(
                f"Tool '{tool_class.__name__}' must provide a class attribute 'tool_name' (str) for its registration name."
            )
        if tool_name in self._tools:
            raise ValueError(f"Tool '{tool_name}' is already registered.")
        self._tools[tool_name] = {
            "function": instance.run,
            "class": tool_class,
            "instance": instance,
        }

    def unregister_tool(self, name: str):
        if name in self._tools:
            del self._tools[name]

    def disable_tool(self, name: str):
        self.unregister_tool(name)

    # ------------------------------------------------------------------
    # Lookup helpers used by ToolsAdapterBase
    # ------------------------------------------------------------------
    def get_tool(self, name: str):
        from janito.tools.disabled_tools import is_tool_disabled

        if name in self._tools and not is_tool_disabled(name):
            return self._tools[name]["instance"]
        return None

    def list_tools(self):
        from janito.tools.disabled_tools import is_tool_disabled

        return [
            name
            for name, entry in self._tools.items()
            if self.is_tool_allowed(entry["instance"]) and not is_tool_disabled(name)
        ]

    def get_tool_classes(self):
        from janito.tools.disabled_tools import is_tool_disabled

        return [
            entry["class"]
            for entry in self._tools.values()
            if self.is_tool_allowed(entry["instance"])
            and not is_tool_disabled(entry["instance"].tool_name)
        ]

    def get_tools(self):
        from janito.tools.disabled_tools import is_tool_disabled

        return [
            entry["instance"]
            for entry in self._tools.values()
            if self.is_tool_allowed(entry["instance"])
            and not is_tool_disabled(entry["instance"].tool_name)
        ]

    # ------------------------------------------------------------------
    # Tool execution with error handling
    # ------------------------------------------------------------------
    def execute_tool(self, name: str, **kwargs):
        """
        Execute a tool with proper error handling.

        This method extends the base execute_tool functionality by adding
        error handling for RuntimeError exceptions that may be raised by
        tools with loop protection decorators.

        Args:
            name: The name of the tool to execute
            **kwargs: Arguments to pass to the tool

        Returns:
            The result of the tool execution

        Raises:
            ToolCallException: If tool execution fails for any reason
            ValueError: If the tool is not found or not allowed
        """
        # First check if tool exists and is allowed
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found or not allowed.")

        # Record tool usage
        self.tool_tracker.record(name, kwargs)

        # Execute the tool using execute_by_name which handles loop protection
        return self.execute_by_name(name, arguments=kwargs)

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------
    def add_tool(self, tool):
        """Register an *instance* (instead of a class) as a tool."""
        if not hasattr(tool, "run") or not callable(tool.run):
            raise TypeError(f"Tool '{tool}' must implement a callable 'run' method.")
        tool_name = getattr(tool, "tool_name", None)
        if not tool_name or not isinstance(tool_name, str):
            raise ValueError(
                f"Tool '{tool}' must provide a 'tool_name' (str) attribute."
            )
        if tool_name in self._tools:
            raise ValueError(f"Tool '{tool_name}' is already registered.")
        self._tools[tool_name] = {
            "function": tool.run,
            "class": tool.__class__,
            "instance": tool,
        }


# -------------------------------------------------------------------------
# Decorator helper for quick registration of local tools
# -------------------------------------------------------------------------


def register_local_tool(tool=None):
    """Class decorator that registers the tool on the *singleton* adapter.

    Example
    -------
    >>> @register_local_tool
    ... class MyTool(BaseTool):
    ...     ...
    """

    def decorator(cls):
        # Register the tool on a *fresh* adapter instance to avoid circular
        # import issues during package initialisation.  This keeps behaviour
        # identical to the original implementation while still allowing
        # immediate use via the singleton in janito.tools.adapters.local.
        LocalToolsAdapter().register_tool(cls)
        return cls

    if tool is None:
        return decorator
    return decorator(tool)
