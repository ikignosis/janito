from textual.widgets import Static
from textual.containers import Container
from typing import List, Optional, Callable

class SelectionPanel(Static):
    def __init__(self, letter: str, summary: str, description: List[str], files: List[str], on_select: Optional[Callable] = None):
        super().__init__()
        self.letter = letter
        self.summary = summary
        self.description = description
        self.files = files
        self.selected = False
        self.on_select = on_select

    def compose(self):
        with Container(classes="panel"):
            yield Static(f"Option {self.letter}: {self.summary}", classes="title")
            with Container(classes="description"):
                for desc in self.description:
                    yield Static(f"• {desc}")
            yield Static("\nAffected files:", classes="files-header")
            with Container(classes="files"):
                for file in self.files:
                    yield Static(f"• {file}")

    def toggle_selected(self):
        self.selected = not self.selected
        self.update_styles()
        if self.selected and self.on_select:
            self.on_select()

    def update_styles(self):
        self.styles.background = "blue" if self.selected else ""