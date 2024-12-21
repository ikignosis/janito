from pathlib import Path
from typing import Optional, Tuple, List
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich.columns import Columns
from rich import box
from janito.common import progress_send_message
from janito.change.history import save_changes_to_history
from janito.config import config
from janito.workspace.workset import Workset
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
    """Process a change request through the main flow."""
    console = Console()
    workset = Workset()
    workset.show()

    # Get analysis of the request using workset content
    analysis = analyze_request(request)
    if not analysis:
        console.print("[red]Analysis failed or interrupted[/red]")
        return False, None

    # Build and send prompt
    prompt = build_change_request_prompt(request, analysis.format_option_text())
    response = progress_send_message(prompt)
    if not response:
        console.print("[red]Failed to get response from AI[/red]")
        return False, None

    # Save to history and process response
    history_file = save_changes_to_history(response, request)

    # Parse changes
    changes = parse_response(response)
    if not changes:
        console.print("[yellow]No changes found in response[/yellow]")
        return False, None

    # Show request and response info
    response_info = extract_response_info(response)
    console.print("\n")
    console.print(Columns([
        Panel(request, title="User Request", border_style="cyan", box=box.ROUNDED),
        Panel(
            response_info if response_info else "No additional information provided",
            title="Response Information",
            border_style="green",
            box=box.ROUNDED
        )
    ], equal=True, expand=True))
    console.print("\n")

    if preview_only:
        preview_all_changes(console, changes)
        return True, history_file

    # Apply changes
    preview_dir = setup_workspace_dir_preview()
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