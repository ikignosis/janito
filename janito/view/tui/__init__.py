""""TUI implementation for Janito views."""

from typing import Dict, Optional, List
from textual.app import App
from janito.change.analysis.options import AnalysisOption
from janito.change.parser import FileChange
from .flows import SelectionFlow, ContentFlow, ChangesFlow

class TuiView:
    """TUI view implementation"""
    def show_content(self, content: str) -> None:
        """Show content in TUI mode"""
        app = TuiApp(content=content)
        app.run()

    def show_options(self, options: Dict[str, AnalysisOption]) -> Optional[str]:
        """Show options and get selection"""
        app = TuiApp(options=options)
        app.run()
        return app.selected_option

    def show_changes(self, changes: List[FileChange]) -> None:
        """Show changes preview"""
        app = TuiApp(changes=changes)
        app.run()

class TuiApp(App):
    """Main TUI application"""
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