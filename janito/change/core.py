from pathlib import Path
from typing import Optional, Tuple, Optional, List
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich.columns import Columns
from rich import box

from janito.common import progress_send_message
from janito.change.history import save_changes_to_history
from janito.config import config
from janito.workspace.scan import collect_files_content
from .viewer import preview_all_changes
from janito.workspace.analysis import analyze_workspace_content as show_content_stats

from . import (
    build_change_request_prompt,
    parse_response,
    setup_workspace_dir_preview,
    ChangeApplier
)

from .analysis import analyze_request

def process_change_request(
    request: str,
    preview_only: bool = False,
    debug: bool = False
    ) -> Tuple[bool, Optional[Path]]:
    """
    Process a change request through the main flow.
    Return:
        success: True if the request was processed successfully
        history_file: Path to the saved history file
    """
    console = Console()
    paths_to_scan = config.include if config.include else [config.workspace_dir]

    content_xml = collect_files_content(paths_to_scan)

    # Show workspace content preview
    show_content_stats(content_xml)

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

    # Extract response info after END_OF_INSTRUCTIONS
    response_info = extract_response_info(response)

    # Show request and response info in panels
    request_panel = Panel(
        request,
        title="User Request",
        border_style="cyan",
        box=box.ROUNDED
    )
    response_panel = Panel(
        response_info if response_info else "No additional information provided",
        title="Response Information",
        border_style="green",
        box=box.ROUNDED
    )

    # Display panels side by side
    columns = Columns([request_panel, response_panel], equal=True, expand=True)
    console.print("\n")
    console.print(columns)
    console.print("\n")

    if preview_only:
        preview_all_changes(console, changes)
        return True, history_file

    # Create preview directory and apply changes
    _, preview_dir = setup_workspace_dir_preview()
    applier = ChangeApplier(preview_dir, debug=debug)

    success, _ = applier.apply_changes(changes)
    if success:
        preview_all_changes(console, changes)

        if not config.auto_apply:
            apply_changes = Confirm.ask("[cyan]Apply changes to working dir?[/cyan]")
        else:
            apply_changes = True
            console.print("[cyan]Auto-applying changes to working dir...[/cyan]")

        if apply_changes:
            applier.apply_to_workspace_dir(changes)
            console.print("[green]Changes applied successfully[/green]")
        else:
            console.print("[yellow]Changes were not applied[/yellow]")

    return success, history_file


def extract_response_info(response: str) -> str:
    """Extract information after END_OF_INSTRUCTIONS marker"""
    if not response:
        return ""

    # Find the marker
    marker = "END_INSTRUCTIONS"
    marker_pos = response.find(marker)

    if marker_pos == -1:
        return ""

    # Get text after marker, skipping the marker itself
    info = response[marker_pos + len(marker):].strip()

    # Remove any XML-style tags
    info = info.replace("<Extra info about what was implemented/changed goes here>", "")

    return info.strip()