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
import tempfile
import time

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
        self.console = Console()

    def validate_change(self, change: FileChange) -> Tuple[bool, Optional[str]]:
        """Validate a FileChange object before applying it"""
        if not change.path:
            return False, "File path is required"

        if change.operation not in ['create_file', 'replace_file', 'remove_file', 'rename_file', 'modify_file']:
            return False, f"Invalid operation: {change.operation}"

        if change.operation == 'rename_file' and not change.new_path:
            return False, "New file path is required for rename operation"

        if change.operation in ['create_file', 'replace_file']:
            if not change.content:
                return False, f"Content is required for {change.operation} operation"

        if change.operation == 'modify_file':
            if not change.modifications:
                return False, "Modifications are required for modify operation"
            for mod in change.modifications:
                if not mod.search_content:
                    return False, "Search content is required for modifications"

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
                console.print(f"\n[red]Invalid change for {change.path}: {error}[/red]")
                return False, set()
        
        # Track modified files and apply changes
        modified_files: Set[Path] = set()
        for change in changes:
            if config.verbose:
                console.print(f"[dim]Previewing changes for {change.path}...[/dim]")
            success, error = self.apply_single_change(change)
            if not success:
                console.print(f"\n[red]Error previewing {change.path}: {error}[/red]")
                return False, modified_files
            if not change.operation == 'remove_file':
                modified_files.add(change.path)
            elif change.operation == 'rename_file':
                modified_files.add(change.new_path)

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
        path = self.preview_dir / change.path
        
        # Ensure preview directory exists and file is copied before modifications
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy original file to preview directory if it doesn't exist and it's not a create operation
        if not path.exists() and change.operation != 'create_file':
            original_path = Path(change.path)
            if original_path.exists():
                if self.console:
                    self.console.print(f"[dim]Copying {original_path} to preview directory {path}[/dim]")
                path.write_text(original_path.read_text())
            else:
                if self.console:
                    self.console.print(f"[red]Original file not found: {original_path}[/red]")
                return False, f"Original file not found: {original_path}"

        # For replace operations, get original content before replacing
        if change.operation == 'replace_file': 
            if not path.exists():
                return False, f"Cannot replace non-existent file {path}"
            # Store original content in the change object for preview purposes
            current_content = path.read_text()
            change.original_content = current_content
            if change.content is not None:
                path.write_text(change.content)
            return True, None
            
        # Handle preview-only operations
        if change.operation == 'remove_file':
            if path.exists():
                current_content = path.read_text()
                if self.console:
                    path.unlink()
            return True, None

        if change.operation in ('create_file', 'replace_file'):
            path.parent.mkdir(parents=True, exist_ok=True)
            if change.operation == 'create_file' and path.exists():
                return False, f"Cannot create file {path} - already exists"
            if change.content is not None:
                path.write_text(change.content)
            return True, None

        if change.operation == 'rename_file':
            new_preview_path = self.preview_dir / change.new_path
            new_preview_path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                return False, f"Cannot rename non-existent file {path}"
            current_content = path.read_text()
            if path.exists():
                path.rename(new_preview_path)
            return True, None

        # Handle modify operation
        if not path.exists():
            return False, f"Cannot modify non-existent file {path}"

        current_content = path.read_text()
        modified = current_content

        for mod in change.modifications:
            if self.console:
                self._print_modification_debug(mod)

            if mod.search_content not in modified:
                lines = modified.splitlines()
                search_lines = mod.search_content.splitlines()
                # Lets attempt a line by line match starting at modified line: 12 (1 based)
                for i, line in enumerate(lines):
                    if i < 12:
                        continue
                    match_line = search_lines[i-11]
                    print(f"Line {i+1}: {repr(line)}\n vs \n{repr(match_line)}\n")
                    if line == match_line:
                        self.console.print(f"\n[yellow]Search text found in line {i+1}[/yellow]")
                    else:
                        self.console.print(f"\n[yellow]Search text not found in line {i+1}[/yellow]")
                        exit(0)
                exit(0)

                content_with_ws = '\n'.join(f'{i+1:3d} | {line.replace(" ", "·")}↵'
                                          for i, line in enumerate(lines))
                self.console.print(f"\n[yellow]File content ({len(lines)} lines, with whitespace):[/yellow]")
                self.console.print(Panel(content_with_ws))
                return False, f"Could not find search text in {path}"

            if mod.replace_content:
                # Update modified content without rereading from disk
                start = modified.find(mod.search_content)
                end = start + len(mod.search_content)                
                modified = modified[:start] + mod.replace_content + modified[end:]
            else:
                # Delete case - Update modified content without rereading from disk
                start = modified.find(mod.search_content)
                end = start + len(mod.search_content)                
                modified = modified[:start] + mod.replace_content + modified[end:]
            return True, None
                
        if modified == current_content:
            if self.console:
                self.console.print("\n[yellow]No changes were applied to the file[/yellow]")
            return False, "No changes were applied"
            
        if self.console:
            self.console.print("\n[green]Changes applied successfully[/green]")
            
        # Write final modified content only once at the end
        path.write_text(modified)
        return True, None

    def _print_modification_debug(self, mod: Modification) -> None:
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