from abc import ABC, abstractmethod

class ToolBase(ABC):
    """
    Base class for all tools. Inherit from this class to implement a new tool.
    """
    def __init__(self):
        self.progress_messages = []
        self._progress_callback = None  # Will be set by ToolHandler if available

    @abstractmethod
    def call(self, **kwargs):
        """
        Trigger the tool's action. Must be implemented by subclasses.
        """
        pass

    def update_progress(self, message: str):
        """
        Report progress. Subclasses can override this to customize progress reporting.
        """
        self.progress_messages.append(message)
        if hasattr(self, '_progress_callback') and self._progress_callback:
            self._progress_callback({'event': 'progress', 'message': message})
