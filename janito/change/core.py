from pathlib import Path
from typing import Optional, Tuple, List, Union
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich.columns import Columns
from rich import box
from janito.config import config
from janito.workspace.workset import Workset
from simple_format_parser.file_operations import CreateFile, DeleteFile, RenameFile
from simple_format_parser.modify_file import ModifyFile
from .executor import execute_operations, Operation

def process_change_request(
    request: str,
    preview_only: bool = False,
    debug: bool = False,
    single: bool = False
) -> Tuple[bool, Optional[Path]]:
    """Process a change request through the main flow."""
    console = Console()
    workset = Workset()
    workset.show()

    # Setup preview directory
    preview_dir = config.workspace_dir / '.preview'
    preview_dir.mkdir(parents=True, exist_ok=True)

    # Create list to hold operations
    preview_operations: List[Operation] = []

    # TODO: Parse the request and create operations
    # Example:
    # preview_operations.append(CreateFile(str(preview_dir / "new_file.txt"), "content"))
    # modifier = ModifyFile(str(preview_dir / "existing.py"))
    # modifier.prepare()
    # modifier.ReplaceBlock(...)
    # preview_operations.append(modifier)

    if preview_only:
        # TODO: Show preview of changes
        return True, None

    # Execute changes in preview dir
    try:
        execute_operations(preview_operations)
        
        # Show preview and confirm
        # TODO: Implement preview display

        if config.auto_apply:
            console.print("[cyan]Auto-applying changes to working dir...[/cyan]")
            apply_changes = True
        else:
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

    except Exception as e:
        console.print(f"[red]Error applying changes: {e}[/red]")
        return False, None