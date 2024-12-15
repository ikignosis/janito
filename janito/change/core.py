from pathlib import Path
from typing import Optional, Tuple, Optional, List
from rich.console import Console
from rich.prompt import Confirm

from janito.common import progress_send_message
from janito.change.history import save_changes_to_history
from janito.config import config
from janito.scan import collect_files_content
from .viewer import preview_all_changes
from .text_applier import TextChangeApplier

from . import (
    build_change_request_prompt,
    parse_response,
    setup_workdir_preview,
    ChangeApplier
)

from .analysis import analyze_request

def process_change_request(
    request: str,
    preview_only: bool = False
    ) -> Tuple[bool, Optional[Path]]:
    """
    Process a change request through the main flow.
    Return:
        success: True if the request was processed successfully
        history_file: Path to the saved history file
    """
    console = Console()
    paths_to_scan = config.include if config.include else [config.workdir]

    content_xml = collect_files_content(paths_to_scan)

    analysis = analyze_request(request, content_xml)
    if not analysis:
        console.print("[red]Analysis failed or interrupted[/red]")
        return False, None

    prompt = build_change_request_prompt(request, analysis.format_option_text(), content_xml)
    response = progress_send_message(prompt)
    if not response:
        console.print("[red]Failed to get response from AI[/red]")
        return False, None

    history_file = save_changes_to_history(response, request)

    # Parse changes
    changes = parse_response(response)
    if not changes:
        console.print("[yellow]No changes found in response[/yellow]")
        return False, None

    if preview_only:
        preview_all_changes(console, changes)
        return True, history_file

    # Create preview directory and apply changes
    _, preview_dir = setup_workdir_preview()
    applier = ChangeApplier(preview_dir)

    success, _ = applier.apply_changes(changes)
    if success:
        preview_all_changes(console, changes)

        if not config.auto_apply:
            apply_changes = Confirm.ask("[cyan]Apply changes to working dir?[/cyan]", default=False)
        else:
            apply_changes = True
            console.print("[cyan]Auto-applying changes to working dir...[/cyan]")

        if apply_changes:
            applier.apply_to_workdir(changes)
            console.print("[green]Changes applied successfully[/green]")
        else:
            console.print("[yellow]Changes were not applied[/yellow]")

    return success, history_file

def play_saved_changes(history_file: Path, preview_only: bool = False) -> Tuple[bool, Optional[Path]]:
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
        
    try:
        content = history_file.read_text()
        changes = parse_response(content)
        
        if not changes:
            console.print("[yellow]No changes found in history file[/yellow]")
            return False, None
            
        if preview_only:
            preview_all_changes(console, changes)
            return True, history_file
            
        # Create preview directory and apply changes
        _, preview_dir = setup_workdir_preview()
        applier = ChangeApplier(preview_dir)
        
        success, _ = applier.apply_changes(changes)
        if success:
            preview_all_changes(console, changes)
            
            if not config.auto_apply:
                apply_changes = Confirm.ask("[cyan]Apply changes to working dir?[/cyan]", default=False)
            else:
                apply_changes = True
                console.print("[cyan]Auto-applying changes to working dir...[/cyan]")
                
            if apply_changes:
                applier.apply_to_workdir(changes)
                console.print("[green]Changes applied successfully[/green]")
            else:
                console.print("[yellow]Changes were not applied[/yellow]")
                
        return success, history_file
        
    except Exception as e:
        console.print(f"[red]Error playing changes: {str(e)}[/red]")
        return False, None