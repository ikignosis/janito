""""Flow screens for TUI navigation."""

from typing import Dict, List
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Header, Footer, Static
from rich.panel import Panel
from rich.text import Text
from rich import box
from pathlib import Path
from janito.change.analysis.options import AnalysisOption
from janito.change.parser import FileChange
from janito.change.viewer.styling import format_content
from janito.change.viewer.panels import (
    create_change_panel,
    create_new_file_panel,
    create_replace_panel,
    create_remove_file_panel
)

class BaseFlow(Screen):
    """Base class for flow screens"""
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

    def action_quit(self):
        self.app.exit()

    def action_previous(self):
        self.scroll_up()

    def action_next(self):
        self.scroll_down()

class SelectionFlow(BaseFlow):
    """Selection screen with direct navigation"""
    def __init__(self, options: Dict[str, AnalysisOption]):
        super().__init__()
        self.options = options
        self.current_index = 0
        self.panels = []

    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            for letter, option in self.options.items():
                panel = Static(self._format_option(letter, option))
                self.panels.append(panel)
                yield panel
        yield Footer()

    def _format_option(self, letter: str, option: AnalysisOption) -> Panel:
        """Format option content"""
        content = Text()
        content.append(f"Option {letter} - {option.summary}\n\n")
        content.append("Description:\n")
        for item in option.description_items:
            content.append(f"• {item}\n")
        content.append("\nAffected files:\n")
        for file in option.affected_files:
            content.append(f"• {file}\n")
        return Panel(content, title=f"Option {letter}", border_style="cyan")

class ContentFlow(BaseFlow):
    """Content viewing flow"""
    def __init__(self, content: str):
        super().__init__()
        self.content = content

    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            yield Static(Panel(
                self.content,
                title="Content View",
                border_style="cyan"
            ))
        yield Footer()

class ChangesFlow(BaseFlow):
    """Changes preview flow"""
    def __init__(self, changes: List[FileChange]):
        super().__init__()
        self.changes = changes

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
                        yield Static(create_change_panel(
                            mod.search_content,
                            mod.replace_content,
                            change.description,
                            1
                        ))
        yield Footer()