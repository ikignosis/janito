from pathlib import Path
from typing import Optional, Tuple, List, Union
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich.columns import Columns
from rich import box
from janito.config import config
from janito.workspace import workset
from janito.simple_format_parser.file_operations import CreateFile, DeleteFile, RenameFile
from janito.simple_format_parser.modify_file_content import ModifyFileContent
from janito.simple_format_parser.executor import Executor
from .prompts import build_change_request_prompt
from .analysis.analyze import analyze_request
from ..common import progress_send_message
from .history import save_changes_to_history

def process_change_request(
    request: str,
    preview_only: bool = False,
    debug: bool = False,
    single: bool = False
) -> Tuple[bool, Optional[Path]]:

    """Process a change request through the main flow."""
    selected_option = analyze_request(request, single=single)

    console = Console()

    preview_dir = workset.setup_preview_directory()
    prompt = build_change_request_prompt(request, selected_option.action_plan_text)
    response = progress_send_message(prompt)
    save_changes_to_history(response, request)
    executor = Executor([CreateFile, DeleteFile, RenameFile, ModifyFileContent], target_dir=preview_dir)
    for i, line in enumerate(response.splitlines()):
        if "CHANGES_START_HERE" in line:
            changes_start = i
        if "END_OF_CHANGES" in line:
            changes_end = i
    reponse_lines = response.splitlines()
    changes_content = reponse_lines[changes_start:changes_end]
    executor.execute('\n'.join(changes_content))

    exit(0)

    apply_changes = Confirm.ask(
        "[cyan]Apply changes to working directory?[/cyan]",
        default=False,
        show_default=True
    )

    if apply_changes:
        # Create workspace operations with updated paths
        workspace_operations: List[Operation] = []
        for op in preview_operations:
            rel_path = Path(op.name).relative_to(preview_dir)
            workspace_path = config.workspace_dir / rel_path
            
            if isinstance(op, CreateFile):
                workspace_operations.append(CreateFile(str(workspace_path), op.content))
            elif isinstance(op, DeleteFile):
                workspace_operations.append(DeleteFile(str(workspace_path)))
            elif isinstance(op, RenameFile):
                rel_target = Path(op.new_name).relative_to(preview_dir)
                workspace_target = config.workspace_dir / rel_target
                workspace_operations.append(RenameFile(str(workspace_path), str(workspace_target)))
            elif isinstance(op, ModifyFile):
                modifier = ModifyFile(str(workspace_path))
                modifier.modifications = op.modifications
                workspace_operations.append(modifier)

        execute_operations(workspace_operations)
        console.print("[green]Changes applied successfully[/green]")
    else:
        console.print("[yellow]Changes were not applied[/yellow]")

    return True, None

