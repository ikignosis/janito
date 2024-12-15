from pathlib import Path
from typing import Optional, Tuple, Optional, List
from rich.console import Console
from rich.prompt import Confirm

from janito.common import progress_send_message
from janito.change.history import save_changes_to_history
from janito.config import config
from janito.scan import collect_files_content
from .viewer import preview_all_changes
from .text_applier import TextChangeApplier  # Add this import

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

    analysis = analyze_request(request, content_xml)
    # handle ctrl-c interrupt
    if not analysis:
        console.print("[red]Analysis failed or interrupted[/red]")
        return False, None
    
    # TODO: We need a better way of selecting filenames from the original content
    # For now, we'll just use the first file

    # Build and send request
    prompt = build_change_request_prompt(request, analysis.format_option_text(), content_xml)
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
    
    # Show change summary
    from .summary import ChangeSummary
    summary = ChangeSummary()
    for change in changes:
        summary.add_change(change.operation.name.title(), change.name)
    summary.display()
    
    # Apply changes to preview
    success, _ = applier.apply_changes(changes)
    if success:
        preview_all_changes(console, changes)  # Use the preview function from viewer module
        # Apply to working dir if requested
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
            
    return success

def play_saved_changes(
    filepath: Path,
) -> bool:
    """Process changes from a saved file - either debug failed finds or apply normal changes."""
    content = filepath.read_text()
    console = Console()
    
    if '_failed' in filepath.name:
        # Debug failed finds only
        applier = TextChangeApplier(console)
        filepath_str, search_text, file_content = applier.extract_debug_info(content)
        if not (filepath_str and search_text and file_content):
            console.print("[red]Could not extract debug information from saved file[/red]")
            return False
            
        applier.debug_failed_finds(search_text, file_content, filepath_str)
        return True
        
    # Regular changes file - process normally
    _, preview_dir = setup_workdir_preview()
    applier = ChangeApplier(preview_dir)
    text_applier = TextChangeApplier(console)  # Create separate applier for failed finds
    config.debug = True  # Enable debug mode for better feedback
    
    try:
        changes = parse_response(content)
        if not changes:
            console.print("[yellow]No changes found in saved file[/yellow]")
            return False
            
        success, error = applier.apply_changes(changes)
        if not success and error and 'Search text not found' in error:
            # Extract details from error message for failed find debugging
            file_path = error.split(': ')[0]
            search_text = error.split(': ')[1]
            try:
                file_content = (preview_dir / file_path).read_text()
                text_applier._handle_failed_search(Path(file_path), search_text, file_content)
            except Exception as e:
                console.print(f"[red]Failed to generate debug file: {e}[/red]")
            return False
            
        if success and not config.auto_apply:
            apply_changes = Confirm.ask("[cyan]Apply changes to working dir?[/cyan]", default=False)
            if apply_changes:
                applier.apply_to_workdir(changes)
                console.print("[green]Changes applied successfully[/green]")
            else:
                console.print("[yellow]Changes were not applied[/yellow]")
                
        return success
    finally:
        config.debug = False  # Restore debug setting