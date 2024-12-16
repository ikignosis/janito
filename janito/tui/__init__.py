"""Terminal User Interface package for Janito."""
from .base import BaseTuiApp
from typing import Dict, Optional
from janito.change.analysis.options import AnalysisOption

class TuiApp(BaseTuiApp):
    """Main TUI application with flow-based navigation"""

    def on_mount(self) -> None:
        """Initialize appropriate flow based on input"""
        if self.options:
            from .flows.selection import SelectionFlow
            self.push_screen(SelectionFlow(self.options))
        elif self.changes:
            from .flows.changes import ChangesFlow
            self.push_screen(ChangesFlow(self.changes))
        elif self.content:
            from .flows.content import ContentFlow
            self.push_screen(ContentFlow(self.content))

__all__ = ['TuiApp']