"""
Applies file changes to preview directory and runs tests

The following situations should result in error:
- Creating a file that already exists
- Replace operation on a non-existent file
- Rename operation on a non-existent file
- Modify operation with search text not found
- No changes applied to a file
"""

from pathlib import Path
from typing import Tuple, Optional, List, Set
from rich.console import Console
from rich.panel import Panel
from rich import box
import subprocess
from ..validator import validate_python_syntax
from .workdir import apply_changes as apply_to_workdir_impl
from janito.config import config
from .file import FileChangeApplier
from .text import TextChangeApplier
from ..parser import FileChange, ChangeOperation
from ..validator import validate_all_changes


class ChangeApplier:
    def __init__(self, preview_dir: Path):
        self.preview_dir = preview_dir
        self.console = Console()
        self.file_applier = FileChangeApplier(preview_dir, self.console)
        self.text_applier = TextChangeApplier(self.console)

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
        
        # Validate all changes using consolidated validator
        is_valid, error = validate_all_changes(changes, set(Path(c.name) for c in changes))
        if not is_valid:
            console.print(f"\n[red]{error}[/red]")
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

        # Validate Python syntax (skip deleted files)
        python_files = {f for f in modified_files if f.suffix == '.py'}
        for change in changes:
            if change.operation == ChangeOperation.REMOVE_FILE:
                python_files.discard(change.name)  # Skip validation for deleted files

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
        path = self.preview_dir / change.name  # Changed back from path to name
        
        # Handle file operations first
        if change.operation != ChangeOperation.MODIFY_FILE:
            return self.file_applier.apply_file_operation(change)

        # Handle text modifications
        if not path.exists():
            original_path = Path(change.name)  # Changed back from path to name
            if not original_path.exists():
                return False, f"Original file not found: {original_path}"
            if self.console:
                self.console.print(f"[dim]Copying {original_path} to preview directory {path}[/dim]")
            path.write_text(original_path.read_text())

        current_content = path.read_text()
        success, modified_content, error = self.text_applier.apply_modifications(
            current_content, 
            change.text_changes, 
            path
        )

        if not success:
            return False, error

        path.write_text(modified_content)
        return True, None

    def apply_to_workdir(self, changes: List[FileChange]) -> bool:
        """Apply changes from preview to working directory"""
        return apply_to_workdir_impl(changes, self.preview_dir, Console())