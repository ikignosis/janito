from typing import Optional
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Header, Footer, Static, Markdown
from rich.console import Console
from rich.markdown import Markdown as RichMarkdown

class QAViewerApp(App):
    """TUI app for displaying Q&A responses."""

    CSS = """
    Screen {
        align: center middle;
    }

    #content {
        width: 100%;
        height: 100%;
        border: solid blue;
    }
    """

    def __init__(self, content: str):
        super().__init__()
        self.content = content
        self._console = Console()

    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer(id="content"):
            yield Static(RichMarkdown(self.content))
        yield Footer()

def show_qa_tui(content: str) -> None:
    """Show Q&A response in TUI mode"""
    app = QAViewerApp(content)
    app.run()