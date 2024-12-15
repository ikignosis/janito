from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.binding import Binding
from ..components import SelectionPanel
from ..navigation import KeyboardNavigator

class SelectionFlow(Screen):
    """Screen for option selection flow"""
    CSS = """
    Container.panel {
        margin: 1;
        padding: 1;
        border: solid $primary;
        width: 100%;
    }

    Static.title {
        text-style: bold;
        color: $secondary;
    }

    Container.description {
        margin-left: 2;
        margin-top: 1;
    }

    Static.files-header {
        margin-top: 1;
        color: $secondary;
    }

    Container.files {
        margin-left: 2;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit"),
        Binding("enter", "select", "Select"),
        Binding("tab", "next", "Next"),
        Binding("shift+tab", "previous", "Previous"),
    ]

    def __init__(self, options: dict):
        super().__init__()
        self.options = options
        self.panels = []
        self.navigator = None

    def compose(self) -> ComposeResult:
        with Container():
            for letter, option in self.options.items():
                panel = SelectionPanel(
                    letter,
                    option.summary,
                    option.description_items,
                    option.affected_files
                )
                self.panels.append(panel)
                yield panel
        self.navigator = KeyboardNavigator(self.panels)

    def action_next(self):
        self.navigator.next_panel()

    def action_previous(self):
        self.navigator.previous_panel()

    def action_select(self):
        current_panel = self.navigator.get_current_panel()
        if current_panel:
            selected_letter = current_panel.letter
            self.app.selected_option = self.options[selected_letter]
            self.app.exit()

    def action_quit(self):
        self.app.selected_option = None
        self.app.exit()