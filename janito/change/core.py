from pathlib import Path
from typing import Optional, Tuple, Optional, List
from rich.console import Console

from janito.common import progress_send_message
from janito.change.history import save_changes_to_history
from janito.config import config
from janito.scan import collect_files_content
from .viewer import preview_all_changes  # Add this import

from . import (
    build_change_request_prompt,
    parse_response,
    setup_workdir_preview,
    ChangeApplier
)

from .analysis import analyze_request

     
def process_change_request(
    request: str,
    ) -> Tuple[bool, Optional[Path]]:
    """
    Process a change request through the main flow.
    Return:
        success: True if the request was processed successfully
        history_file: Path to the saved history file
    """
    console = Console()
    paths_to_scan = config.include if config.include else [config. workdir]

    
    # Analyze request to get change plan
    content_xml = collect_files_content(paths_to_scan)
    analysis = analyze_request(content_xml, request)
    
    # Get affected files content (new only)
    content_xml = collect_files_content(analysis.get_affected_paths(skip_new=True)) if analysis.affected_files else ""
    
    # Build and send request
    prompt = build_change_request_prompt(analysis.format_option_text(), request, content_xml)
    response = progress_send_message(prompt)
    if not response:
        console.print("[red]Failed to get response from AI[/red]")
        return False, None
    
    history_file = save_changes_to_history(response, request)
    return parse_and_apply_changes(response), history_file
    

def parse_and_apply_changes(response: str) -> Tuple[bool, Optional[Path]]:

    # Create preview directory
    _, preview_dir = setup_workdir_preview()
    applier = ChangeApplier(preview_dir)
    
    console = Console()


    # Parse and save response
    changes = parse_response(response)
    if not changes:
        console.print("[yellow]No changes found in response[/yellow]")
        return False, None       
    
    # Apply changes to preview
    success, _ = applier.apply_changes(changes)
    if success:
        preview_all_changes(console, changes)  # Use the preview function from viewer module
        # Apply to working dir if requested
        if console.input("Apply changes to working dir? [y/N] ").lower() == 'y':
            applier.apply_to_workdir(changes)
            console.print("[green]Changes applied successfully[/green]")
        else:
            console.print("[yellow]Changes were not applied[/yellow]")
            
    return success

def play_saved_changes(
    filepath: Path,
) -> bool:
    """Process changes from a saved file through the main flow, skipping analysis/request steps."""
    response = filepath.read_text()
    return parse_and_apply_changes(response)