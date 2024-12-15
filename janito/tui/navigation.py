from typing import List
from textual.widgets import Static
from .components import SelectionPanel

class KeyboardNavigator:
    def __init__(self, panels: List[SelectionPanel]):
        self.panels = panels
        self.current_index = 0
        self._init_selection()

    def _init_selection(self):
        if self.panels:
            self.panels[0].toggle_selected()

    def next_panel(self):
        if not self.panels:
            return
        self.panels[self.current_index].toggle_selected()
        self.current_index = (self.current_index + 1) % len(self.panels)
        self.panels[self.current_index].toggle_selected()

    def previous_panel(self):
        if not self.panels:
            return
        self.panels[self.current_index].toggle_selected()
        self.current_index = (self.current_index - 1) % len(self.panels)
        self.panels[self.current_index].toggle_selected()

    def get_current_panel(self) -> SelectionPanel:
        return self.panels[self.current_index] if self.panels else None