from pathlib import Path
from typing import Tuple, Optional
from rich.console import Console
from rich.prompt import Confirm
from .preview import setup_workspace_dir_preview
from .applier.main import ChangeApplier
from .viewer import preview_all_changes  # Add this import
from ..config import config  # Add this import
from ..file_operations import FileOperationExecutor


def play_saved_changes(history_file: Path) -> Tuple[bool, Optional[Path]]:
    """
    Replay changes from a saved history file
    Returns:
        success: True if changes were applied successfully
        history_file: Path to the history file that was played
    """
    console = Console()

    if not history_file.exists():
        console.print(f"[red]History file not found: {history_file}[/red]")
        return False, None

    response = history_file.read_text(encoding='utf-8')
    preview_dir = setup_workspace_dir_preview()
    for i, line in enumerate(response.splitlines()):
        if "CHANGES_START_HERE" in line:
            changes_start = i + 1
        if "END_OF_CHANGES" in line:
            changes_end = i - 1
    reponse_lines = response.splitlines()
    changes_content = reponse_lines[changes_start:changes_end]
    changes_content = '\n'.join(changes_content)

    # Create preview directory and apply changes
    preview_dir = setup_workspace_dir_preview()
    applier = ChangeApplier(preview_dir, changes_content, debug=True)
    success, _ = applier.apply_changes()
    if success:
        preview_all_changes(applier.file_oper_exec.instances)

        if not config.auto_apply:
            apply_changes = Confirm.ask("[cyan]Apply changes to working dir?[/cyan]", default=False)
        else:
            apply_changes = True
            console.print("[cyan]Auto-applying changes to working dir...[/cyan]")

        if apply_changes:
            applier.apply_to_workspace_dir(changes)
            console.print("[green]Changes applied successfully[/green]")
        else:
            console.print("[yellow]Changes were not applied[/yellow]")
            return False, history_file

        return success, history_file