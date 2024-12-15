from pathlib import Path
from typing import Tuple, Optional
from rich.console import Console
from .parser import FileChange, ChangeOperation

class FileChangeApplier:
    def __init__(self, preview_dir: Path, console: Console = None):
        self.preview_dir = preview_dir
        self.console = console or Console()

    def apply_file_operation(self, change: FileChange) -> Tuple[bool, Optional[str]]:
        """Apply a file operation (create/replace/remove/rename)
        Returns: (success, error_message)"""
        path = self.preview_dir / change.name
        path.parent.mkdir(parents=True, exist_ok=True)

        # Store original content before any changes
        if path.exists():
            change.original_content = path.read_text()

        if change.operation == ChangeOperation.REMOVE_FILE:
            return self._handle_remove(path)
        elif change.operation in (ChangeOperation.CREATE_FILE, ChangeOperation.REPLACE_FILE):
            return self._handle_create_replace(path, change)
        elif change.operation == ChangeOperation.RENAME_FILE:
            return self._handle_rename(path, change)

        return False, f"Unsupported operation: {change.operation}"

    def _handle_remove(self, path: Path) -> Tuple[bool, Optional[str]]:
        """Handle file removal"""
        if path.exists():
            path.unlink()
        return True, None

    def _handle_create_replace(self, path: Path, change: FileChange) -> Tuple[bool, Optional[str]]:
        """Handle file creation or replacement"""
        if change.operation == ChangeOperation.CREATE_FILE and path.exists():
            return False, f"Cannot create file {path} - already exists"

        if change.content is not None:
            path.write_text(change.content)
            return True, None

        return False, "No content provided for create/replace operation"

    def _handle_rename(self, path: Path, change: FileChange) -> Tuple[bool, Optional[str]]:
        """Handle file rename"""
        if not path.exists():
            return False, f"Cannot rename non-existent file {path}"

        if not change.target:
            return False, "No target path provided for rename operation"

        new_path = self.preview_dir / change.target
        new_path.parent.mkdir(parents=True, exist_ok=True)
        path.rename(new_path)
        return True, None