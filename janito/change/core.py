from pathlib import Path
from typing import Optional, Tuple, List, Union
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich.columns import Columns
from rich import box
from janito.config import config
from janito.workspace import workset
from janito.file_operations import CreateFile, DeleteFile, RenameFile, ReplaceFile, ModifyFile
from janito.file_operations import FileOperationExecutor
from .prompts import build_change_request_prompt
from .analysis.analyze import analyze_request
from ..common import progress_send_message
from .history import save_changes_to_history
from .viewer.panels import preview_all_changes
from .applier.main import ChangeApplier

def process_change_request(
    request: str,
    preview_only: bool = False,
    debug: bool = False,
    single: bool = False
) -> Tuple[bool, Optional[Path]]:

    """Process a change request through the main flow."""
    console = Console()
    selected_option = analyze_request(request, single=single)

    preview_dir = workset.setup_preview_directory()
    prompt = build_change_request_prompt(request, selected_option.action_plan_text)
    response = progress_send_message(prompt)
    save_changes_to_history(response, request)
    
    # Extract changes content from response
    for i, line in enumerate(response.splitlines()):
        if "CHANGES_START_HERE" in line:
            changes_start = i + 1
        if "CHANGES_END_HERE" in line:
            changes_end = i - 1
    response_lines = response.splitlines()
    changes_content = '\n'.join(response_lines[changes_start:changes_end])

    # Use ChangeApplier to handle the changes
    applier = ChangeApplier(preview_dir, changes_content, debug=debug)
    success, _ = applier.apply_changes()
    
    if success:
        preview_all_changes(applier.file_oper_exec.instances)

        if not preview_only:
            if not config.auto_apply:
                apply_changes = Confirm.ask(
                    "[cyan]Apply changes to working directory?[/cyan]",
                    default=False,
                    show_default=True
                )
            else:
                apply_changes = True
                console.print("[cyan]Auto-applying changes to working dir...[/cyan]")

            if apply_changes:
                applier.apply_to_workspace_dir()
                console.print("[green]Changes applied successfully[/green]")
            else:
                console.print("[yellow]Changes were not applied[/yellow]")

    return success, None

