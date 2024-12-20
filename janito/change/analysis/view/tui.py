from typing import Dict, Optional
from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import Header, Footer, Static, Button
from textual.screen import Screen
from rich.console import Console
from rich.text import Text
from ..options import AnalysisOption
from .terminal import _create_option_content

class AnalysisApp(App):
    """TUI app for displaying and selecting analysis options."""

    CSS = """
    Screen {
        align: center middle;
    }

    #options {
        width: 100%;
        height: auto;
    }

    Button {
        margin: 1;
        width: auto;
    }
    """

    def __init__(self, options: Dict[str, AnalysisOption]):
        super().__init__()
        self.options = options
        self.selected_option: Optional[str] = None
        self._console = Console()

    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer(id="options"):
            for letter, option in sorted(self.options.items()):
                yield Static(_create_option_content(option))
            with Container():
                for letter in sorted(self.options.keys()):
                    yield Button(f"Option {letter}", id=f"opt_{letter}")
                yield Button("Modify Request", id="modify")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events"""
        button_id = event.button.id
        if button_id == "modify":
            self.selected_option = "M"
        elif button_id.startswith("opt_"):
            self.selected_option = button_id[-1]
        self.exit()

def show_analysis_tui(options: Dict[str, AnalysisOption]) -> Optional[str]:
    """Show analysis options in TUI mode and return selected option"""
    app = AnalysisApp(options)
    app.run()
    return app.selected_option