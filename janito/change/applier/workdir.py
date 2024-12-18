from pathlib import Path
from typing import Set, List
import shutil
from rich.console import Console
from janito.config import config
from ..parser import FileChange, ChangeOperation

def verify_changes(changes: List[FileChange]) -> tuple[bool, str]:
    """Verify changes can be safely applied to workdir.
    Returns (is_safe, error_message)."""
    for change in changes:
        target_path = config.workdir / change.name
        if change.operation == ChangeOperation.CREATE_FILE and target_path.exists():
            return False, f"Cannot create {change.name} - already exists"
        elif change.operation != ChangeOperation.CREATE_FILE and not target_path.exists():
            return False, f"Cannot modify non-existent file {change.name}"
    return True, ""

def apply_changes(changes: List[FileChange], preview_dir: Path, console: Console) -> bool:
    """Apply all changes from preview to workdir.
    Returns success status."""
    is_safe, error = verify_changes(changes)
    if not is_safe:
        console.print(f"[red]Error: {error}[/red]")
        return False

    console.print("\n[blue]Applying changes to working directory...[/blue]")

    for change in changes:
        if change.operation == ChangeOperation.REMOVE_FILE:
            remove_from_workdir(change.name, console)
        else:
            filepath = change.target if change.operation == ChangeOperation.RENAME_FILE else change.name
            target_path = config.workdir / filepath
            preview_path = preview_dir / filepath

            target_path.parent.mkdir(parents=True, exist_ok=True)
            if preview_path.exists():
                shutil.copy2(preview_path, target_path)
                console.print(f"[dim]Applied changes to {filepath}[/dim]")

    return True

def remove_from_workdir(filepath: Path, console: Console) -> None:
    """Remove file from working directory"""
    target_path = config.workdir / filepath
    if target_path.exists():
        target_path.unlink()
        console.print(f"[red]Removed {filepath}[/red]")