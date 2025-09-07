from janito.report_events import ReportEvent, ReportSubtype, ReportAction
from janito.event_bus.bus import event_bus as default_event_bus

import inspect
from collections import namedtuple


class ToolPermissions(namedtuple("ToolPermissions", ["read", "write", "execute"])):
    __slots__ = ()

    def __new__(cls, read=False, write=False, execute=False):
        return super().__new__(cls, read, write, execute)

    def __repr__(self):
        return f"ToolPermissions(read={self.read}, write={self.write}, execute={self.execute})"


class ToolBase:
    """
    Base class for all tools in the janito project.
    Extend this class to implement specific tool functionality.
    """

    permissions: "ToolPermissions" = None  # Required: must be set by subclasses

    def __init__(self, name=None, event_bus=None):
        if self.permissions is None or not isinstance(
            self.permissions, ToolPermissions
        ):
            raise ValueError(
                f"Tool '{self.__class__.__name__}' must define a 'permissions' attribute of type ToolPermissions."
            )
        self.name = name or self.__class__.__name__
        self._event_bus = event_bus or default_event_bus

    @property
    def event_bus(self):
        return self._event_bus

    @event_bus.setter
    def event_bus(self, bus):
        self._event_bus = bus or default_event_bus

    def report_action(self, message: str, action: ReportAction, context: dict = None):
        """
        Report that a tool action is starting. This should be the first reporting call for every tool action.
        """
        self._event_bus.publish(
            ReportEvent(
                subtype=ReportSubtype.ACTION_INFO,
                message="  " + message,
                action=action,
                tool=self.name,
                context=context,
            )
        )

    def report_error(self, message: str, context: dict = None):
        self._event_bus.publish(
            ReportEvent(
                subtype=ReportSubtype.ERROR,
                message=message,
                action=None,
                tool=self.name,
                context=context,
            )
        )

    def report_success(self, message: str, context: dict = None):
        self._event_bus.publish(
            ReportEvent(
                subtype=ReportSubtype.SUCCESS,
                message=message,
                action=None,
                tool=self.name,
                context=context,
            )
        )

    def report_warning(self, message: str, context: dict = None):
        self._event_bus.publish(
            ReportEvent(
                subtype=ReportSubtype.WARNING,
                message=message,
                action=None,
                tool=self.name,
                context=context,
            )
        )

    def report_stdout(self, message: str, context: dict = None):
        self._event_bus.publish(
            ReportEvent(
                subtype=ReportSubtype.STDOUT,
                message=message,
                action=None,
                tool=self.name,
                context=context,
            )
        )

    def report_stderr(self, message: str, context: dict = None):
        self._event_bus.publish(
            ReportEvent(
                subtype=ReportSubtype.STDERR,
                message=message,
                action=None,
                tool=self.name,
                context=context,
            )
        )

    def run(self, *args, **kwargs):
        raise NotImplementedError("Subclasses must implement the run method.")

    def get_signature(self):
        """
        Return the function signature for this tool's run method.
        This is used for introspection and validation.
        """
        return inspect.signature(self.run)
