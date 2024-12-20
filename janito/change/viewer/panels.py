from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich import box
from rich.text import Text
from rich.syntax import Syntax
from typing import List, Union
from ..parser import FileChange, ChangeOperation
from .styling import format_content, create_legend_items
from .content import create_content_preview
from .sections import find_modified_sections
from rich.rule import Rule
import shutil
import sys
from rich.live import Live
from pathlib import Path

def create_progress_header(operation: str, filename: str, current: int, total: int, reason: str = None) -> Text:
    """Create a compact single-line header with balanced layout.

    Args:
        operation: Type of operation being performed (not displayed)
        filename: Name of the file being modified
        current: Current change number
        total: Total number of changes
        reason: Optional reason for the change
    """
    header = Text()

    # Left-aligned progress
    progress = f"Change {current}/{total}"
    header.append(progress, style="bold blue")

    # Center-aligned reason if provided
    if reason:
        # Add padding between progress and reason
        header.append(" │ ", style="dim")
        header.append(reason, style="yellow")

    # Right-aligned filename
    header.append(" │ ", style="dim")
    header.append(str(filename), style="bold white")

    return header

def preview_all_changes(console: Console, changes: List[FileChange]) -> None:
    """Show a summary of all changes with side-by-side comparison and continuous flow."""
    total_changes = len(changes)

    # Show unified legend at the start
    console.print(create_legend_items(console), justify="center")
    console.print()

    # Show initial progress
    console.print("[yellow]Starting changes preview...[/yellow]", justify="center")
    console.print()

    # Show progress indicator
    with Live(console=console, refresh_per_second=4) as live:
        live.update("[yellow]Processing changes...[/yellow]")

    # Group changes by operation type
    grouped_changes = {}
    for change in changes:
        if change.operation not in grouped_changes:
            grouped_changes[change.operation] = []
        grouped_changes[change.operation].append(change)

    # First show file operations (create, remove, rename, move)
    _show_file_operations(console, grouped_changes)

    # Then show side-by-side panels for replacements and modifications
    console.print("\n[bold blue]File Changes:[/bold blue]")

    for i, change in enumerate(changes):
        if change.operation in (ChangeOperation.REPLACE_FILE, ChangeOperation.MODIFY_FILE):
            show_side_by_side_diff(console, change, i, total_changes)

def _show_file_operations(console: Console, grouped_changes: dict) -> None:
    """Display file operation summaries with content preview for new files."""
    # Show file creations first
    if ChangeOperation.CREATE_FILE in grouped_changes:
        console.print("\n[bold green]New Files:[/bold green]")
        for change in grouped_changes[ChangeOperation.CREATE_FILE]:
            console.print(Rule(f"[green]Creating new file: {change.name}[/green]", style="green"), justify="center")
            if change.content:
                preview = create_content_preview(Path(change.name), change.content, is_new=True)
                console.print(preview, justify="center")
            console.print()

    # Show file removals
    if ChangeOperation.REMOVE_FILE in grouped_changes:
        console.print("\n[bold red]File Removals:[/bold red]")
        for change in grouped_changes[ChangeOperation.REMOVE_FILE]:
            console.print(Rule(f"[red]Removing file: {change.name}[/red]", style="red"))
            console.print()

    # Show file renames
    if ChangeOperation.RENAME_FILE in grouped_changes:
        console.print("\n[bold yellow]File Renames:[/bold yellow]")
        for change in grouped_changes[ChangeOperation.RENAME_FILE]:
            console.print(Rule(f"[yellow]Renaming file: {change.name} → {change.target}[/yellow]", style="yellow"))
            console.print()

    # Show file moves
    if ChangeOperation.MOVE_FILE in grouped_changes:
        console.print("\n[bold blue]File Moves:[/bold blue]")
        for change in grouped_changes[ChangeOperation.MOVE_FILE]:
            console.print(Rule(f"[blue]Moving file: {change.name} → {change.target}[/blue]", style="blue"))
            console.print()

def show_side_by_side_diff(console: Console, change: FileChange, change_index: int = 0, total_changes: int = 1) -> None:
    """Show side-by-side diff panels for a file change with continuous flow.

    Args:
        console: Rich console instance
        change: FileChange object containing the changes
        change_index: Current change number (0-based)
        total_changes: Total number of changes
    """
    """Show side-by-side diff panels for a file change with progress tracking and reason

    Args:
        console: Rich console instance
        change: FileChange object containing the changes
        change_index: Current change number (0-based)
        total_changes: Total number of changes
    """
    # Track current file name to prevent unnecessary paging
    # Get terminal dimensions for layout
    term_width = console.width or 120
    min_panel_width = 60  # Minimum width for readable content
    if change.operation == ChangeOperation.REMOVE_FILE:
        show_delete_panel(console, change, change_index, total_changes)
        return
    # Get terminal width for layout decisions
    term_width = console.width or 120
    min_panel_width = 60  # Minimum width for readable content
    can_do_side_by_side = term_width >= (min_panel_width * 2 + 4)  # +4 for padding

    # Get original and new content
    original = change.original_content or ""
    new_content = change.content or ""

    # Split into lines
    original_lines = original.splitlines()
    new_lines = new_content.splitlines()

    operation = change.operation.name.replace('_', ' ').title()
    header = create_progress_header(operation, change.name, change_index + 1, total_changes, change.reason)
    # Display panel with centered content and header
    console.print(Panel(Text.assemble(header, justify="center"), box=box.HEAVY, style="cyan", title_align="center"))

    # Show layout mode indicator
    if not can_do_side_by_side:
        console.print("[yellow]Terminal width is limited. Using vertical layout for better readability.[/yellow]")
        console.print(f"[dim]Recommended terminal width: {min_panel_width * 2 + 4} or greater[/dim]")

    def create_diff_panels(orig_section: List[str], new_section: List[str],
                          change_name: str, can_do_side_by_side: bool, term_width: int) -> List[Panel]:
        """Create unified diff panels for both text and file changes"""
        left_panel = format_content(orig_section, orig_section, new_section, True)
        right_panel = format_content(new_section, orig_section, new_section, False)

        # Calculate optimal panel widths based on content
        if can_do_side_by_side:
            left_max_width = max((len(line) for line in str(left_panel).splitlines()), default=0)
            right_max_width = max((len(line) for line in str(right_panel).splitlines()), default=0)

            # Add padding and margins
            left_width = min(left_max_width + 4, (term_width - 4) // 2)
            right_width = min(right_max_width + 4, (term_width - 4) // 2)

            # Ensure minimum width
            min_width = 30
            left_width = max(left_width, min_width)
            right_width = max(right_width, min_width)
        else:
            left_width = right_width = term_width - 2

        return [
            Panel(
                left_panel or "",
                title="[red]Original[/red]",
                title_align="center",
                subtitle=str(change_name),
                subtitle_align="center",
                padding=(0, 1),
                width=left_width
            ),
            Panel(
                right_panel or "",
                title="[green]Modified[/green]",
                title_align="center",
                subtitle=str(change_name),
                subtitle_align="center",
                padding=(0, 1),
                width=right_width
            )
        ]

    # Handle text changes
    if change.text_changes:
        for text_change in change.text_changes:
            search_lines = text_change.search_content.splitlines() if text_change.search_content else []
            replace_lines = text_change.replace_content.splitlines() if text_change.replace_content else []

            # Find modified sections
            sections = find_modified_sections(search_lines, replace_lines)

            # Show modification type and reason with rich rule
            reason_text = f" - {text_change.reason}" if text_change.reason else ""
            if text_change.search_content and text_change.replace_content:
                console.print(Rule(f" Replace Text{reason_text} ", style="bold cyan", align="center"))
            elif not text_change.search_content:
                console.print(Rule(f" Append Text{reason_text} ", style="bold green", align="center"))
            elif not text_change.replace_content:
                console.print(Rule(f" Delete Text{reason_text} ", style="bold red", align="center"))

            # Format and display each section
            for i, (orig_section, new_section) in enumerate(sections):
                panels = create_diff_panels(orig_section, new_section, change.name,
                                           can_do_side_by_side, term_width)

                if can_do_side_by_side:
                    columns = Columns(panels, equal=True, expand=False)
                    console.print()
                    console.print(columns, justify="center")
                    console.print()
                else:
                    console.print()
                    for panel in panels:
                        console.print(panel, justify="center")
                        console.print()

                # Show separator between sections if not last section
                if i < len(sections) - 1:
                    console.print(Rule(" Section Break ", style="cyan dim", align="center"))
    else:
        # For non-text changes, show full content side by side
        sections = find_modified_sections(original_lines, new_lines)
        for i, (orig_section, new_section) in enumerate(sections):
            panels = create_diff_panels(orig_section, new_section, change.name,
                                       can_do_side_by_side, term_width)

            # Render panels based on layout
            if can_do_side_by_side:
                # Create centered columns with fixed width
                available_width = console.width
                panel_width = (available_width - 4) // 2  # Account for padding
                for panel in panels:
                    panel.width = panel_width

                columns = Columns(panels, equal=True, expand=False)
                console.print(columns, justify="center")
            else:
                for panel in panels:
                    console.print(panel, justify="center")
                    console.print()  # Add spacing between panels

            # Show separator between sections if not last section
            if i < len(sections) - 1:
                console.print(Rule(style="dim"))

            # Update height after displaying content

    # Add final separator and success message
    console.print(Rule(title="End Of Changes", style="bold blue"))
    console.print()
    console.print(Panel("[yellow]You're the best! All changes have been previewed successfully![/yellow]",
                       style="yellow",
                       title="Success",
                       title_align="center"))
    console.print()

def show_delete_panel(console: Console, change: FileChange, change_index: int = 0, total_changes: int = 1) -> None:
    """Show an enhanced panel for file deletion operations with status indicators

    Args:
        console: Rich console instance
        change: FileChange object containing the changes
        change_index: Current change number (0-based)
        total_changes: Total number of changes
    """
    operation = change.operation.name.replace('_', ' ').title()
    header = create_progress_header(operation, change.name, change_index + 1, total_changes, change.reason)
    header.rstrip()  # Remove trailing newlines

    # Add removal icon
    icon_header = Text()
    icon_header.append("🗑️ ", style="bold red")
    icon_header.append(header)

    # Create content text with status indicators
    content = Text()
    content.append("⚠️  ", style="bold yellow")  # Warning icon
    content.append("This file will be permanently removed", style="bold red")
    content.append("\n\n")
    content.append("Status: ", style="bold")
    content.append("Pending Removal", style="red")

    # Show file preview if content exists
    if change.original_content:
        content.append("\n\n")
        content.append("Original Content Preview:", style="dim red")
        content.append("\n")
        syntax = Syntax(
            change.original_content,
            "python",
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
            background_color="red_1"
        )
        content.append(syntax)

    # Display enhanced panels with consistent styling
    console.print(Panel(
        header,
        box=box.HEAVY,
        style="red",
        title="[red]File Removal Operation[/red]",
        title_align="center"
    ))
    console.print(Panel(
        content,
        title="[red]Removal Preview[/red]",
        subtitle="[dim red]This action cannot be undone[/dim red]",
        title_align="center",
        subtitle_align="center",
        border_style="red",
        padding=(1, 2)
    ))
    console.print(Rule(title="End of Removal Preview", style="bold red"))
    console.print()

def get_human_size(size_bytes: int) -> str:
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"

def get_file_stats(content: Union[str, Text]) -> str:
    """Get file statistics in human readable format"""
    if isinstance(content, Text):
        lines = content.plain.splitlines()
        size = len(content.plain.encode('utf-8'))
    else:
        lines = content.splitlines()
        size = len(content.encode('utf-8'))
    return f"{len(lines)} lines, {get_human_size(size)}"