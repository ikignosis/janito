from abc import ABC, abstractmethod


class ToolBase(ABC):
    """
    Base class for all tools. Inherit from this class to implement a new tool.
    """

    def __init__(self):
        self.progress_messages = []
        self._progress_callback = None  # Will be set by ToolHandler if available

    def report_stdout(self, message: str):
        self.update_progress({"type": "stdout", "message": message})

    def report_stderr(self, message: str):
        self.update_progress({"type": "stderr", "message": message})

    @abstractmethod
    def run(self, **kwargs):
        """
        Abstract call method for tool execution. Should be overridden by subclasses.

        Args:
            **kwargs: Arbitrary keyword arguments for the tool.

        Returns:
            Any: The result of the tool execution.
        """
        pass

    def update_progress(self, progress: dict):
        """
        Report progress. Subclasses can override this to customize progress reporting.
        """
        self.progress_messages.append(progress)
        if hasattr(self, "_progress_callback") and self._progress_callback:
            self._progress_callback(progress)

    def report_info(self, message: str):
        self.update_progress(
            {"type": "info", "tool": self.__class__.__name__, "message": message}
        )

    def report_success(self, message: str):
        self.update_progress(
            {"type": "success", "tool": self.__class__.__name__, "message": message}
        )

    def report_error(self, message: str):
        self.update_progress(
            {"type": "error", "tool": self.__class__.__name__, "message": message}
        )

    def report_warning(self, message: str):
        self.update_progress(
            {"type": "warning", "tool": self.__class__.__name__, "message": message}
        )
