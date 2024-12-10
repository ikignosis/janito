from pathlib import Path
from typing import Optional, Tuple, Optional
from rich.console import Console

from janito.common import progress_send_message
from janito.changehistory import save_changes_to_history
from janito.config import config
from janito.scan import collect_files_content

from . import (
    build_change_request_prompt,
    parse_response,
    setup_workdir_preview,
    ChangeApplier
)

from .analysis import analyze_request

def process_change_request(
    request: str,
    test_cmd: Optional[str] = None,
    auto_apply: bool = False
) -> Tuple[bool, Optional[Path]]:
    """Process a change request through the main flow."""
    console = Console()
    
    # Analyze request to get change plan
    analysis = analyze_request(request)
    
    # Get affected files content
    files_content = collect_files_content(analysis.get_affected_paths()) if analysis.affected_files else ""
    
    # Create preview directory
    backup_dir, preview_dir = setup_workdir_preview()
    applier = ChangeApplier(preview_dir)
    
    # Build and send request
    prompt = build_change_request_prompt(analysis.format_option_text(), request, files_content)
    response = progress_send_message(prompt)
    if not response:
        console.print("[red]Failed to get response from AI[/red]")
        return False, None
        
    # Parse and save response
    changes = parse_response(response)
    if not changes:
        console.print("[yellow]No changes found in response[/yellow]")
        return False, None
        
    history_file = save_changes_to_history(response, request)
    
    # Apply changes to preview
    success, modified_files = applier.apply_changes(changes, test_cmd)
    
    if success:
        # Apply if auto_apply or user confirms
        if auto_apply or console.input("Apply changes? [y/N] ").lower() == 'y':
            applier.apply_to_workdir(changes)
            console.print("[green]Changes applied successfully[/green]")
        else:
            console.print("[yellow]Changes were not applied[/yellow]")
            
    return success, history_file