"""
Applies file changes to preview directory and runs tests

The following situations should result in error:
- Creating a file that already exists
- Replace operation on a non-existent file
- Rename operation on a non-existent file
- Modify operation with search text not found
- Invalid regex pattern in modification
- No changes applied to a file
"""

from pathlib import Path
from typing import Tuple, Optional, List, Set
from rich.console import Console
from rich.panel import Panel
from rich import box
import subprocess
import re
import difflib
from .viewer import show_change_preview, preview_all_changes
from .parser import FileChange
from typing import Dict

from janito.config import config
from .parser import FileChange
from .parser import Modification
from .validator import validate_python_syntax
from .position import find_text_positions
from .viewer import preview_all_changes
from .workdir import apply_changes as apply_to_workdir_impl

class ChangeApplier:
    def __init__(self, preview_dir: Path):
        self.preview_dir = preview_dir
        self.console = Console() if config.debug else None

    def validate_change(self, change: FileChange) -> Tuple[bool, Optional[str]]:
        """Validate a FileChange object before applying it"""
        if not change.filepath:
            return False, "File path is required"

        if change.operation not in ['create', 'replace', 'remove', 'rename', 'modify']:
            return False, f"Invalid operation: {change.operation}"

        if change.operation == 'rename' and not change.new_filepath:
            return False, "New file path is required for rename operation"

        if change.operation in ['create', 'replace']:
            if not change.content:
                return False, f"Content is required for {change.operation} operation"

        if change.operation == 'modify':
            if not change.modifications:
                return False, "Modifications are required for modify operation"
            for mod in change.modifications:
                if not mod.search_content:
                    return False, "Search content is required for modifications"
                if mod.search_type not in ['SearchText', 'SearchRegex']:
                    return False, f"Invalid search type: {mod.search_type}"

        return True, None

    def run_test_command(self, test_cmd: str) -> Tuple[bool, str, Optional[str]]:
        """Run test command in preview directory.
        Returns (success, output, error)"""
        try:
            result = subprocess.run(
                test_cmd,
                shell=True,
                cwd=self.preview_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            return (
                result.returncode == 0,
                result.stdout,
                result.stderr if result.returncode != 0 else None
            )
        except subprocess.TimeoutExpired:
            return False, "", "Test command timed out after 5 minutes"
        except Exception as e:
            return False, "", f"Error running test: {str(e)}"

    def apply_changes(self, changes: List[FileChange]) -> tuple[bool, Set[Path]]:
        """Apply changes in preview directory, runs tests if specified.
        Returns (success, modified_files)"""
        console = Console()
        
        # Validate all changes first
        for change in changes:
            is_valid, error = self.validate_change(change)
            if not is_valid:
                console.print(f"\n[red]Invalid change for {change.filepath}: {error}[/red]")
                return False, set()
        
        # Track modified files and apply changes
        modified_files: Set[Path] = set()
        for change in changes:
            if config.verbose:
                console.print(f"[dim]Previewing changes for {change.filepath}...[/dim]")
            success, error = self.apply_single_change(change)
            if not success:
                console.print(f"\n[red]Error previewing {change.filepath}: {error}[/red]")
                return False, modified_files
            if not change.operation == 'remove':
                modified_files.add(change.filepath)
            elif change.operation == 'rename':
                modified_files.add(change.new_filepath)

        # Validate Python syntax
        python_files = {f for f in modified_files if f.suffix == '.py'}
        for filepath in python_files:
            preview_path = self.preview_dir / filepath
            is_valid, error_msg = validate_python_syntax(preview_path.read_text(), preview_path)
            if not is_valid:
                console.print(f"\n[red]Python syntax validation failed for {filepath}:[/red]")
                console.print(f"[red]{error_msg}[/red]")
                return False, modified_files

        # Show success message with syntax validation status
        console.print("\n[cyan]Changes applied successfully.[/cyan]")
        if python_files:
            console.print(f"[green]✓ Python syntax validated for {len(python_files)} file(s)[/green]")
        
        # Run tests if specified
        if config.test_cmd:
            console.print(f"\n[cyan]Testing changes in preview directory:[/cyan] {config.test_cmd}")
            success, output, error = self.run_test_command(test_cmd)
            if output:
                console.print("\n[bold]Test Output:[/bold]")
                console.print(Panel(output, box=box.ROUNDED))
            if not success:
                console.print("\n[red bold]Tests failed in preview.[/red bold]")
                if error:
                    console.print(Panel(error, title="Error", border_style="red"))
                return False, modified_files

        return True, modified_files

    def apply_single_change(self, change: FileChange) -> Tuple[bool, Optional[str]]:
        """Apply a single file change to preview directory"""
        filepath = self.preview_dir / change.filepath
        # Handle preview-only operations
        if change.operation == 'remove':
            if filepath.exists():
                filepath.unlink()
            return True, None

        if change.operation in ('create', 'replace'):
            filepath.parent.mkdir(parents=True, exist_ok=True)
            if change.operation == 'create' and filepath.exists():
                return False, f"Cannot create file {filepath} - already exists"
            if change.operation == 'replace' and not filepath.exists():
                return False, f"Cannot replace non-existent file {filepath}"
            if change.content is not None:
                filepath.write_text(change.content)
            return True, None

        if change.operation == 'rename':
            new_preview_path = self.preview_dir / change.new_filepath
            new_preview_path.parent.mkdir(parents=True, exist_ok=True)
            if not filepath.exists():
                return False, f"Cannot rename non-existent file {filepath}"
            if filepath.exists():
                filepath.rename(new_preview_path)
            return True, None

        # Handle modify operation
        if not filepath.exists():
            return False, f"Cannot modify non-existent file {filepath}"

        content = filepath.read_text()
        modified = content

        for mod in change.modifications:
            if self.console:
                self._print_modification_debug(mod)

            if mod.search_type == 'SearchRegex':
                try:
                    pattern = re.compile(mod.search_content, re.MULTILINE)
                except re.error as e:
                    return False, f"Invalid regex pattern: {str(e)}"
                found_text = pattern.search(modified)
                if not found_text:
                    return False, f"Could not find search text in {filepath}, using regex pattern: {mod.search_content}"
                mod.search_display_content = found_text.group(0)
            else:
                if mod.search_content not in modified:
                    return False, f"Could not find search text in {filepath}"
                mod.search_display_content = mod.search_content

            if mod.replace_content:
                # use find_text_positions to get the start and end positions of the found text and actually replace it
                start, end = find_text_positions(modified, mod.search_display_content)
                modified = modified[:start] + mod.replace_content + modified[end:]
                
        if modified == content:
            if self.console:
                self.console.print("\n[yellow]No changes were applied to the file[/yellow]")
            return False, "No changes were applied"
            
        if self.console:
            self.console.print("\n[green]Changes applied successfully[/green]")
            
        filepath.write_text(modified)
        return True, None

    def _print_modification_debug(self, mod: Modification) -> None:
        """Print debug information for a modification"""
        self.console.print(f"\n[cyan]Processing {mod.search_type} modification[/cyan]")
        self.console.print("[yellow]Search text:[/yellow]")
        self.console.print(Panel(mod.search_content))
        if mod.replace_content is not None:
            self.console.print("[yellow]Replace with:[/yellow]")
            self.console.print(Panel(mod.replace_content))
        else:
            self.console.print("[yellow]Action:[/yellow] Delete text")

    def apply_to_workdir(self, changes: List[FileChange]) -> bool:
        """Apply changes from preview to working directory"""
        return apply_to_workdir_impl(changes, self.preview_dir, Console())

