from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Header, Footer, Static, Markdown
from textual.screen import Screen
from textual.binding import Binding

class ContentView(Static):
    def __init__(self, content: str):
        super().__init__()
        self.content = content

    def compose(self) -> ComposeResult:
        yield Markdown(self.content)

class ContentFlow(Screen):
    """Screen for content viewing flow"""
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