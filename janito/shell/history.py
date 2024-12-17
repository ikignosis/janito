"""Command history management for Janito shell."""
from pathlib import Path
from typing import List, Optional
from prompt_toolkit.history import FileHistory

class CommandHistory:
    """Manages shell command history."""

    def __init__(self, history_file: Optional[Path] = None):
        if history_file is None:
            history_file = Path.home() / ".janito_history"
        self.history = FileHistory(str(history_file))

    def add(self, command: str) -> None:
        """Add a command to history."""
        self.history.append_string(command)

    def get_last(self, n: int = 10) -> List[str]:
        """Get last n commands from history."""
        return list(self.history.get_strings())[-n:]