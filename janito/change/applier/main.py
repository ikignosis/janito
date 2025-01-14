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
from .validator import validate_python_syntax, validation_count, validation_success
from typing import Tuple, Optional, List, Set, Union
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich import box
from shutil import get_terminal_size
import subprocess
from .workspace_dir import apply_changes as apply_to_workspace_dir_impl
from janito.config import config
from janito.file_operations import CreateFile, DeleteFile, RenameFile, ReplaceFile, ModifyFile
from janito.file_operations import FileOperationExecutor


class ChangeApplier:
    """Handles applying changes to files."""

    def __init__(self, preview_dir: Path, changes_text: str, debug: bool = False):
        self.preview_dir = preview_dir
        self.changes_text = changes_text
        self.debug = debug
        self.console = Console()
        self.file_oper_exec = FileOperationExecutor(target_dir=self.preview_dir)

    def run_test_command(self, test_cmd: str) -> Tuple[bool, str, Optional[str]]:
        """Run test command in preview directory.
        Returns (success, output, error)
        """
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

    def apply_changes(self) -> tuple[bool, Set[Path]]:
        """Apply changes in preview directory, runs tests if specified.
        Returns (success, modified_files)"""
        console = Console()
        self.file_oper_exec.execute(self.changes_text)

        # Track modified files and validate Python syntax
        modified_files = {Path(op.name) for op in self.file_oper_exec.instances}

        # Validate Python files syntax
        for file_path in modified_files:
            if file_path.suffix == '.py':
                is_valid, error = validate_python_syntax(self.preview_dir / file_path)
                if not is_valid:
                    console.print(f"\n[red]Syntax error in {file_path}:[/red] {error}")
                    return False, modified_files

        if validation_count > 0:
            console.print(f"\n[green]Syntax validation successful for {validation_success}/{validation_count} Python files[/green]")

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

    def apply_to_workspace_dir(
        self, 
    ) -> bool:
        """Apply changes from preview to working directory"""
        changes = self.file_oper_exec.instances
        return apply_to_workspace_dir_impl(changes, self.preview_dir, Console())

    def confirm_and_apply_to_workspace(self) -> bool:
        """Handles confirmation and application of changes to workspace directory.
        Returns True if changes were applied successfully."""
        
        if not config.auto_apply:
            # Get terminal width and calculate padding
            term_width = get_terminal_size().columns
            prompt_text = "[cyan]Apply changes to working directory?[/cyan]"
            padding = (term_width - len(prompt_text) + 20) // 2  # +20 to account for color codes
            apply_changes = Confirm.ask(
                "\n" + " " * max(0, padding) + prompt_text,
                default=False,
                show_default=True
            )
        else:
            apply_changes = True
            self.console.print("[cyan]Auto-applying changes to working dir...[/cyan]", justify="center")

        if apply_changes:
            success = self.apply_to_workspace_dir()
            if success:
                self.console.print("[green]Changes applied successfully[/green]", justify="center")
            return success
        else:
            self.console.print("[yellow]Changes were not applied[/yellow]", justify="center")
            return False
