from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Header, Footer, Static
from rich.text import Text
from typing import List
from ..change.viewer.styling import format_content, create_legend_items
from ..change.viewer.panels import create_change_panel, create_new_file_panel, create_replace_panel, create_remove_file_panel
from ..change.parser import FileChange

class ChangeViewer(Screen):
    CSS = """
    ScrollableContainer {
        width: 100%;
        height: 100%;
        border: solid green;
        background: $surface;
        color: $text;
        padding: 1;
    }
    
    Container.panel {
        margin: 1;
        padding: 1;
        border: solid $primary;
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit"),
        Binding("up", "previous", "Previous"),
        Binding("down", "next", "Next"),
    ]

    def __init__(self, changes: List[FileChange]):
        super().__init__()
        self.changes = changes
        self.current_index = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            for change in self.changes:
                if change.operation == 'create_file':
                    yield Static(create_new_file_panel(change.name, change.content))
                elif change.operation == 'replace_file':
                    yield Static(create_replace_panel(change.name, change))
                elif change.operation == 'remove_file':
                    yield Static(create_remove_file_panel(change.name))
                elif change.operation == 'modify_file':
                    for mod in change.text_changes:
                        yield Static(create_change_panel(mod.search_content, mod.replace_content, change.description, 1))
        yield Footer()

    def action_quit(self):
        self.app.exit()

    def action_previous(self):
        self.scroll_up()

    def action_next(self):
        self.scroll_down()