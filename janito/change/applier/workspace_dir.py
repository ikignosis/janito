from pathlib import Path
from typing import Set, List
import shutil
import os
from rich.console import Console
from janito.config import config
from ..parser import FileChange, ChangeOperation

def verify_changes(changes: List[FileChange]) -> tuple[bool, str]:
    """Verify changes can be safely applied to workspace_dir.
    Returns (is_safe, error_message)."""
    # Validate operation order
    last_operation = None
    for change in changes:
        last_operation = change.operation

        source_path = config.workspace_dir / change.name

        if change.operation == ChangeOperation.CREATE_FILE:
            if source_path.exists():
                return False, f"Cannot create {change.name} - already exists"

        elif change.operation in (ChangeOperation.MOVE_FILE, ChangeOperation.RENAME_FILE):
            if not source_path.exists():
                return False, f"Cannot {change.operation.name.lower()} non-existent file {change.name}"
            target_path = config.workspace_dir / change.target
            if target_path.exists():
                return False, f"Cannot {change.operation.name.lower()} {change.name} to {change.target} - target already exists"

    return True, ""

def apply_changes(changes: List[FileChange], preview_dir: Path, console: Console) -> bool:
    """Apply all changes from preview to workspace_dir in the correct order.
    Returns success status."""
    is_safe, error = verify_changes(changes)
    if not is_safe:
        console.print(f"[red]Error: {error}[/red]")
        return False

    console.print("\n[blue]Applying changes to working directory...[/blue]")

    # Apply file operations
    for change in changes:
        if change.operation == ChangeOperation.REMOVE_FILE:
            remove_from_workspace_dir(change.name, console)
        else:
            filepath = change.target if change.operation == ChangeOperation.RENAME_FILE else change.name
            target_path = config.workspace_dir / filepath
            preview_path = preview_dir / filepath

            target_path.parent.mkdir(parents=True, exist_ok=True)
            if preview_path.exists():
                shutil.copy2(preview_path, target_path)
                console.print(f"[dim]Applied changes to {filepath}[/dim]")


    return True

def _is_empty_dir(path: Path) -> bool:
    """Check if directory is empty or contains only __pycache__"""
    if not path.is_dir():
        return False
    contents = list(path.iterdir())
    if not contents:
        return True
    return len(contents) == 1 and contents[0].name == "__pycache__"

def _cleanup_pycache(path: Path) -> None:
    """Recursively remove __pycache__ directory if it exists"""
    pycache = path / "__pycache__"
    if pycache.exists():
        shutil.rmtree(pycache)

def _cleanup_empty_dirs(path: Path, console: Console) -> None:
    """Recursively remove empty parent directories"""
    current = path
    while current != config.workspace_dir:
        if _is_empty_dir(current):
            _cleanup_pycache(current)
            try:
                current.rmdir()
                console.print(f"[dim]Removed empty directory {current.relative_to(config.workspace_dir)}[/dim]")
            except OSError:
                break
        current = current.parent

def remove_from_workspace_dir(filepath: Path, console: Console) -> None:
    """Remove file from working directory and cleanup empty parent directories"""
    target_path = config.workspace_dir / filepath
    if target_path.exists():
        target_path.unlink()
        console.print(f"[red]Removed {filepath}[/red]")
        # Clean up parent directories if empty
        _cleanup_empty_dirs(target_path.parent, console)