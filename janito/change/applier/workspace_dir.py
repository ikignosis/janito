from pathlib import Path
from typing import List, Union
import shutil
import os
from rich.console import Console
from janito.config import config
from janito.file_operations import CreateFile, DeleteFile, RenameFile, ReplaceFile, ModifyFile


def apply_changes(changes: List[Union[CreateFile, DeleteFile, RenameFile, ReplaceFile, ModifyFile]], 
                 preview_dir: Path, console: Console) -> bool:
    """Apply all changes from preview to workspace_dir in the correct order.
    Returns success status."""

    console.print("\n[blue]Applying changes to working directory...[/blue]")

    # Process changes in order: Delete -> Rename -> Create/Replace/Modify
    changes_by_type = {
        DeleteFile: [],
        RenameFile: [],
        'other': []  # CreateFile, ReplaceFile, ModifyFile
    }

    # Group changes by type for ordered processing
    for change in changes:
        if isinstance(change, DeleteFile):
            changes_by_type[DeleteFile].append(change)
        elif isinstance(change, RenameFile):
            changes_by_type[RenameFile].append(change)
        else:
            changes_by_type['other'].append(change)

    # Process deletes first
    for change in changes_by_type[DeleteFile]:
        remove_from_workspace_dir(change.name, console)

    # Process renames second
    for change in changes_by_type[RenameFile]:
        target_path = config.workspace_dir / change.new_name
        preview_path = preview_dir / change.new_name
        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if preview_path.exists():
            shutil.copy2(preview_path, target_path)
            console.print(f"[dim]Renamed {change.name} to {change.new_name}[/dim]")
            
        # Remove the old file if it exists
        old_path = config.workspace_dir / change.name
        if old_path.exists():
            old_path.unlink()

    # Process creates/replaces/modifies last
    for change in changes_by_type['other']:
        target_path = config.workspace_dir / change.name
        preview_path = preview_dir / change.name

        target_path.parent.mkdir(parents=True, exist_ok=True)
        if preview_path.exists():
            shutil.copy2(preview_path, target_path)
            if isinstance(change, CreateFile):
                console.print(f"[green]Created {change.name}[/green]")
            else:
                console.print(f"[dim]Applied changes to {change.name}[/dim]")

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

def remove_from_workspace_dir(filepath: str, console: Console) -> None:
    """Remove file from working directory and cleanup empty parent directories"""
    target_path = config.workspace_dir / filepath
    if target_path.exists():
        target_path.unlink()
        console.print(f"[red]Removed {filepath}[/red]")
        # Clean up parent directories if empty
        _cleanup_empty_dirs(target_path.parent, console)