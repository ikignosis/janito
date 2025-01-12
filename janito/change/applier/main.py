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
from .workspace_dir import apply_changes as apply_to_workspace_dir_impl
from janito.config import config
from ..models import FileChange, ChangeOperation


class ChangeApplier:
    """Handles applying changes to files."""

    def __init__(self, preview_dir: Path, changes_text: str, debug: bool = False):
        self.preview_dir = preview_dir
        self.changes_text = changes_text
        self.debug = debug
        self.console = Console()

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

    def apply_changes(self, debug: bool = None) -> tuple[bool, Set[Path]]:
        """Apply changes in preview directory, runs tests if specified.
        Returns (success, modified_files)"""
        console = Console()
        from janito.simple_parser.executor import Executor
        from janito.simple_parser.file_operations import RenameFile, CreateFile, DeleteFile
        from janito.simple_parser.modify_file_content import ModifyFileContent
        executor = Executor([RenameFile, CreateFile, DeleteFile, ModifyFileContent], target_dir=self.preview_dir)
        executor.execute(self.changes_text)

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


    def apply_to_workspace_dir(self, changes: List[FileChange], debug: bool = None) -> bool:
        """Apply changes from preview to working directory"""
        debug = debug if debug is not None else self.debug
        return apply_to_workspace_dir_impl(changes, self.preview_dir, Console())