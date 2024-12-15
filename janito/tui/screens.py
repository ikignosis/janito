from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import Button, Header, Footer, Static, Markdown
from textual.screen import Screen
from textual.binding import Binding
from .selection import SelectionScreen
from typing import List
from janito.change.parser import FileChange


class ContentView(Static):
    def __init__(self, content: str):
        super().__init__()
        self.content = content

    def compose(self) -> ComposeResult:
        yield Markdown(self.content)

class ContentScreen(Screen):
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit"),
    ]

    def __init__(self, content: str):
        super().__init__()
        self.content = content

    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            yield ContentView(self.content)
        yield Footer()

    def action_quit(self):
        self.app.exit()

class TuiApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
    
    ScrollableContainer {
        width: 100%;
        height: 100%;
        border: solid green;
        background: $surface;
        color: $text;
        padding: 1;
    }
    """

    def __init__(self, content: str = None, options: dict = None, changes: List[FileChange] = None):
        super().__init__()
        self.content = content
        self.options = options
        self.changes = changes
        self.selected_option = None

    def on_mount(self) -> None:
        if self.options:
            self.push_screen(SelectionScreen(self.options))
        elif self.changes:
            self.push_screen(ChangeViewer(self.changes))
        elif self.content:
            self.push_screen(ContentScreen(self.content))