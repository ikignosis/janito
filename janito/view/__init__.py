""""View package for Janito UI components."""

from typing import Dict, Optional, List
from rich.console import Console
from janito.change.analysis.options import AnalysisOption
from janito.change.parser import FileChange

class ViewManager:
    """Base class for view management"""
    def __init__(self):
        self.console = Console()

    def show_content(self, content: str) -> None:
        """Display content using console"""
        self.console.print(content)

    def show_options(self, options: Dict[str, AnalysisOption]) -> Optional[str]:
        """Display options using console"""
        self.console.print(options)
        return None

    def show_changes(self, changes: List[FileChange]) -> None:
        """Display changes preview using console"""
        from janito.change.viewer.panels import preview_all_changes
        preview_all_changes(self.console, changes)

# Create singleton instance
view_manager = ViewManager()