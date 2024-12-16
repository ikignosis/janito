from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Header, Footer, Static
from typing import Dict, Optional
from rich.panel import Panel
from rich import box
from janito.change.analysis.options import AnalysisOption
from janito.agents import agent
from janito.common import progress_send_message
from janito.change.parser import parse_response
from .changes import ChangesFlow

class SelectionFlow(Screen):
    """Selection screen with direct navigation to changes preview"""

    CSS = """
    #options-container {
        layout: horizontal;
        height: 100%;
        margin: 1;
        align: center middle;
    }

    .option-panel {
        width: 1fr;
        height: 100%;
        border: solid $primary;
        margin: 0 1;
        padding: 1;
    }

    .option-panel.selected {
        border: double $secondary;
        background: $boost;
    }
    """

    BINDINGS = [
        Binding("left", "previous", "Previous"),
        Binding("right", "next", "Next"),
        Binding("enter", "select", "Select"),
        Binding("escape", "quit", "Quit"),
    ]

    def __init__(self, options: Dict[str, AnalysisOption]):
        super().__init__()
        self.options = options
        self.current_index = 0
        self.panels = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="options-container"):
            for letter, option in self.options.items():
                panel = Static(self._format_option(letter, option), classes="option-panel")
                self.panels.append(panel)
                yield panel
        yield Footer()
        # Set initial selection
        if self.panels:
            self.panels[0].add_class("selected")

    def _format_option(self, letter: str, option: AnalysisOption) -> str:
        """Format option content"""
        content = [f"Option {letter}: {option.summary}\n"]
        content.append("\nDescription:")
        for item in option.description_items:
            content.append(f"• {item}")
        content.append("\nAffected files:")
        for file in option.affected_files:
            content.append(f"• {file}")
        return "\n".join(content)

    def action_previous(self) -> None:
        """Handle left arrow key"""
        if self.panels:
            self.panels[self.current_index].remove_class("selected")
            self.current_index = (self.current_index - 1) % len(self.panels)
            self.panels[self.current_index].add_class("selected")

    def action_next(self) -> None:
        """Handle right arrow key"""
        if self.panels:
            self.panels[self.current_index].remove_class("selected")
            self.current_index = (self.current_index + 1) % len(self.panels)
            self.panels[self.current_index].add_class("selected")

    def action_select(self) -> None:
        """Handle enter key - request changes and show preview"""
        if self.panels:
            letter = list(self.options.keys())[self.current_index]
            option = self.options[letter]

            # Build and send change request
            from janito.change import build_change_request_prompt
            from janito.scan import collect_files_content

            files_content = collect_files_content([option.get_clean_path(f) for f in option.affected_files])
            prompt = build_change_request_prompt(option.format_option_text(), "", files_content)
            response = progress_send_message(prompt)

            if response:
                changes = parse_response(response)
                if changes:
                    # Show changes preview
                    self.app.push_screen(ChangesFlow(changes))
                    return

            self.app.selected_option = option
            self.app.exit()

    def action_quit(self) -> None:
        """Handle escape key"""
        self.app.selected_option = None
        self.app.exit()