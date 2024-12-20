from typing import Optional, List
from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import Header, Footer, Static
from rich.console import RenderableType
from rich.text import Text
from ..parser import FileChange
from .panels import preview_all_changes
from rich.console import Console

class ChangePreviewApp(App):
    """TUI app for previewing file changes."""

    CSS = """
    Screen {
        align: center middle;
    }

    #content {
        width: 100%;
        height: 100%;
        border: solid green;
    }
    """

    def __init__(self, changes: List[FileChange]):
        super().__init__()
        self.changes = changes
        self._console = Console()

    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer(id="content"):
            with Container():
                yield Static(self._render_changes())
        yield Footer()

    def _render_changes(self) -> RenderableType:
        """Render changes preview using existing preview function"""
        preview_all_changes(self._console, self.changes)
        return self._console.export_text()

def show_changes_tui(changes: List[FileChange]) -> None:
    """Show changes in TUI mode"""
    app = ChangePreviewApp(changes)
    app.run()