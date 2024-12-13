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
from .parser import FileChange, TextChange
from .validator import validate_python_syntax
from .position import find_text_positions
from .workdir import apply_changes as apply_to_workdir_impl
from janito.config import config

class ChangeApplier:
    def __init__(self, preview_dir: Path):
        self.preview_dir = preview_dir
        self.console = Console()

    def validate_change(self, change: FileChange) -> Tuple[bool, Optional[str]]:
        """Validate a FileChange object before applying it"""
        if not change.name:
            return False, "File name is required"
    
        if change.operation not in ['create_file', 'replace_file', 'remove_file', 'rename_file', 'modify_file']:
            return False, f"Invalid operation: {change.operation}"

        if change.operation == 'rename_file' and not change.target:
            return False, "Target file path is required for rename operation"

        if change.operation in ['create_file', 'replace_file']:
            if not change.content:
                return False, f"Content is required for {change.operation} operation"

        if change.operation == 'modify_file':
            if not change.text_changes:
                return False, "Modifications are required for modify operation"
            for change in change.text_changes:
                if not change.search_content and not change.replace_content:
                    return False, "Search or replace content is required for modification"

                # Validate regex pattern
                try:
                    re.compile(change.search_content)
                except re.error as e:
                    return False, f"Invalid regex pattern in modification: {str(e)}"

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
                console.print(f"\n[red]Invalid change for {change.name}: {error}[/red]")
                return False, set()
        
        # Track modified files and apply changes
        modified_files: Set[Path] = set()
        for change in changes:
            if config.verbose:
                console.print(f"[dim]Previewing changes for {change.name}...[/dim]")
            success, error = self.apply_single_change(change)
            if not success:
                console.print(f"\n[red]Error previewing {change.name}: {error}[/red]")
                return False, modified_files
            if not change.operation == 'remove_file':
                modified_files.add(change.name)
            elif change.operation == 'rename_file':
                modified_files.add(change.target)

        # Validate Python syntax
        python_files = {f for f in modified_files if f.suffix == '.py'}
        for path in python_files:
            preview_path = self.preview_dir / path
            is_valid, error_msg = validate_python_syntax(preview_path.read_text(), preview_path)
            if not is_valid:
                console.print(f"\n[red]Python syntax validation failed for {path}:[/red]")
                console.print(f"[red]{error_msg}[/red]")
                return False, modified_files

        # Show success message with syntax validation status
        console.print("\n[cyan]Changes applied successfully.[/cyan]")
        if python_files:
            console.print(f"[green]✓ Python syntax validated for {len(python_files)} file(s)[/green]")
        
        # Run tests if specified
        if config.test_cmd:
            console.print(f"\n[cyan]Testing changes in preview directory:[/cyan] {config.test_cmd}")
            success, output, error = self.run_test_command(config.test_cmd)
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
        path = self.preview_dir / change.name
        
        # Ensure preview directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Handle file existence check first
        if not path.exists() and change.operation not in ['create_file', 'replace_file']:
            original_path = Path(change.name)
            if not original_path.exists():
                return False, f"Original file not found: {original_path}"
            if self.console:
                self.console.print(f"[dim]Copying {original_path} to preview directory {path}[/dim]")
            path.write_text(original_path.read_text())

        # Handle operations
        if change.operation == 'remove_file':
            if path.exists():
                path.unlink()
            return True, None

        if change.operation in ('create_file', 'replace_file'):
            if change.operation == 'create_file' and path.exists():
                return False, f"Cannot create file {path} - already exists"
            if change.content is not None:
                path.write_text(change.content)
            return True, None

        if change.operation == 'rename_file':
            if not path.exists():
                return False, f"Cannot rename non-existent file {path}"
            new_preview_path = self.preview_dir / change.target
            new_preview_path.parent.mkdir(parents=True, exist_ok=True)
            path.rename(new_preview_path)
            return True, None

        # Handle modify operation
        if change.operation == 'modify_file':
            if not path.exists():
                return False, f"Cannot modify non-existent file {path}"

            current_content = path.read_text()
            modified = current_content

            for mod in change.text_changes:
                if self.console:
                    self._print_modification_debug(mod)

                # means append to the end of the file
                if not mod.search_content:
                    modified += mod.replace_content
                    continue

                if mod.search_content not in modified:
                    # Debug search content not found
                    lines = modified.splitlines()
                    content_with_ws = '\n'.join(f'{i+1:3d} | {line.replace(" ", "·")}↵'
                                              for i, line in enumerate(lines))
                    self.console.print(f"\n[yellow]File content ({len(lines)} lines, with whitespace):[/yellow]")
                    self.console.print(Panel(content_with_ws))
                    return False, f"Could not find search text in {path}"

                if mod.replace_content is not None:
                    # Replace case
                    start = modified.find(mod.search_content)
                    end = start + len(mod.search_content)                
                    modified = modified[:start] + mod.replace_content + modified[end:]
                else:
                    # Delete case
                    start = modified.find(mod.search_content)
                    end = start + len(mod.search_content)                
                    modified = modified[:start] + modified[end:]

            if modified == current_content:
                if self.console:
                    self.console.print("\n[yellow]No changes were applied to the file[/yellow]")
                return False, "No changes were applied"
                
            # Write changes and return success
            path.write_text(modified)
            if self.console:
                self.console.print("\n[green]Changes applied successfully[/green]")
            return True, None

    def _print_modification_debug(self, mod: TextChange) -> None:
        """Print debug information for a modification"""
        self.console.print("\n[cyan]Processing modification[/cyan]")
        
        # Format search text with line numbers
        search_text_lines = mod.search_content.splitlines()
        formatted_search = '\n'.join(f'{i+1:3d} | {line.replace(" ", "·")}↵' 
                                   for i, line in enumerate(search_text_lines))
        self.console.print(f"[yellow]Search text ({len(search_text_lines)} lines, · for space, ↵ for newline):[/yellow]")
        self.console.print(Panel(formatted_search))
        
        if mod.replace_content is not None:
            # Format replace text with line numbers
            replace_text_lines = mod.replace_content.splitlines()
            formatted_replace = '\n'.join(f'{i+1:3d} | {line.replace(" ", "·")}↵'
                                      for i, line in enumerate(replace_text_lines))
            self.console.print(f"[yellow]Replace with ({len(replace_text_lines)} lines, · for space, ↵ for newline):[/yellow]")
            self.console.print(Panel(formatted_replace))
        else:
            self.console.print("[yellow]Action:[/yellow] Delete text")

    def apply_to_workdir(self, changes: List[FileChange]) -> bool:
        """Apply changes from preview to working directory"""
        return apply_to_workdir_impl(changes, self.preview_dir, Console())