from pathlib import Path
from typing import Tuple, Optional
from rich.console import Console
from rich.prompt import Confirm
from .preview import setup_workspace_dir_preview
from .applier.main import ChangeApplier
from .viewer.panels import show_all_changes
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
        if "CHANGES_END_HERE" in line:
            changes_end = i - 1
    reponse_lines = response.splitlines()
    changes_content = reponse_lines[changes_start:changes_end]
    changes_content = '\n'.join(changes_content)

    # Create preview directory and apply changes
    preview_dir = setup_workspace_dir_preview()
    applier = ChangeApplier(preview_dir, changes_content, debug=True)
    success, _ = applier.apply_changes()
    if success:
        show_all_changes(applier.file_oper_exec.instances)
        
        success = applier.confirm_and_apply_to_workspace()
        return success, history_file if success else None

    return False, None
