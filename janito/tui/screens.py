from textual.app import App
from .flows import SelectionFlow, ContentFlow, ChangesFlow
from typing import List, Optional, Dict
from janito.change.parser import FileChange
from janito.change.analysis.options import AnalysisOption

class TuiApp(App):
    """Main TUI application with flow-based navigation"""
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

    def on_mount(self) -> None:
        """Initialize appropriate flow based on input"""
        if self.options:
            self.push_screen(SelectionFlow(self.options))
        elif self.changes:
            self.push_screen(ChangesFlow(self.changes))
        elif self.content:
            self.push_screen(ContentFlow(self.content))