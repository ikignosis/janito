from textual.app import App
from typing import List, Optional, Dict
from janito.change.parser import FileChange
from janito.change.analysis.options import AnalysisOption

class BaseTuiApp(App):
    """Base class for TUI applications with common functionality"""
    CSS = """
    Screen {
        align: center middle;
    }
    """

    def __init__(self,
                 content: Optional[str] = None,
                 options: Optional[Dict[str, AnalysisOption]] = None,
                 changes: Optional[List[FileChange]] = None):
        super().__init__()
        self.content = content
        self.options = options
        self.changes = changes
        self.selected_option = None