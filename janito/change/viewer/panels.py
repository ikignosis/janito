from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich import box
from rich.text import Text
from typing import List, Optional
from ..parser import FileChange, ChangeOperation
from .styling import format_content, create_legend_items
from .content import create_content_preview
from rich.rule import Rule
import shutil
import sys
from rich.live import Live
from .pager import check_pager  # Add this import

# Remove clear_last_line, wait_for_space, and check_pager functions since they've been moved

def preview_all_changes(console: Console, changes: List[FileChange]) -> None:
    """Show a summary of all changes with side-by-side comparison and continuous flow."""
    """Show a summary of all changes with side-by-side comparison."""
    total_changes = len(changes)

    # Get terminal height
    term_height = shutil.get_terminal_size().lines

    # Show unified legend at the start
    console.print(create_legend_items(console), justify="center")
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

    # Track content height
    current_height = 2  # Account for legend and newline

    # Show file operations with rule lines and track height
    current_height = _show_file_operations(console, grouped_changes)

    # Then show side-by-side panels for replacements
    console.print("\n[bold blue]File Changes:[/bold blue]")
    current_height += 2

    for i, change in enumerate(changes):
        if change.operation in (ChangeOperation.REPLACE_FILE, ChangeOperation.MODIFY_FILE):
            show_side_by_side_diff(console, change, i, total_changes)

def _show_file_operations(console: Console, grouped_changes: dict) -> int:
    """Display file operation summaries with content preview for new files.

    Tracks current file being displayed and manages continuous flow.
    """
    """Display file operation summaries with content preview for new files."""
    height = 0
    for operation, group in grouped_changes.items():
        for change in group:
            if operation == ChangeOperation.CREATE_FILE:
                console.print(Rule(f"[green]Creating new file: {change.name}[/green]", style="green"))
                height += 1
                if change.content:
                    preview = create_content_preview(change.name, change.content)
                    console.print(preview)
                    height += len(change.content.splitlines()) + 4  # Account for panel borders
            elif operation == ChangeOperation.REMOVE_FILE:
                console.print(Rule(f"[red]Removing file: {change.name}[/red]", style="red"))
                height += 1
            elif operation == ChangeOperation.RENAME_FILE:
                console.print(Rule(f"[yellow]Renaming file: {change.name} → {change.target}[/yellow]", style="yellow"))
                height += 1
            elif operation == ChangeOperation.MOVE_FILE:
                console.print(Rule(f"[blue]Moving file: {change.name} → {change.target}[/blue]", style="blue"))
                height += 1
            height = check_pager(console, height)
    return height

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
    from .pager import set_current_file, get_current_file
    current_file = get_current_file()
    new_file = str(change.name)

    # Only update paging state for different files
    if current_file != new_file:
        set_current_file(new_file)
    # Handle delete operations with special formatting
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

    # Track accumulated height
    current_height = 0

    # Track content height
    current_height += 1

    # Check if we need to page before showing header
    header_height = 3  # Account for panel borders and content
    current_height = check_pager(console, current_height, header_height)

    # Show the header with reason and progress
    operation = change.operation.name.replace('_', ' ').title()
    progress = f"Change {change_index + 1}/{total_changes}"
    # Create centered reason text if present
    reason_text = Text()
    if change.reason:
        reason_text.append("\n")
        reason_text.append(change.reason, style="italic")
    # Build header with operation and progress
    header = Text()
    header.append(f"{operation}:", style="bold cyan")
    header.append(f" {change.name} ")
    header.append(f"({progress})", style="dim")
    header.append(reason_text)
    # Display panel with centered content
    console.print(Panel(header, box=box.HEAVY, style="cyan", title_align="center"))
    current_height += header_height

    # Show layout mode indicator
    if not can_do_side_by_side:
        console.print("[yellow]Terminal width is limited. Using vertical layout for better readability.[/yellow]")
        console.print(f"[dim]Recommended terminal width: {min_panel_width * 2 + 4} or greater[/dim]")

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
                left_panel = format_content(orig_section, orig_section, new_section, True)
                right_panel = format_content(new_section, orig_section, new_section, False)

                # Calculate upcoming content height
                content_height = len(orig_section) + len(new_section) + 4  # Account for panel borders and padding

                # Check if we need to page before showing content
                current_height = check_pager(console, current_height, content_height)

                # Create panels with adaptive width
                if can_do_side_by_side:
                    # Calculate panel width for side-by-side layout
                    panel_width = (term_width - 4) // 2  # Account for padding
                    panels = [
                        Panel(
                            left_panel or "",
                            title="[red]Original Content[/red]",
                            title_align="center",
                            subtitle=str(change.name),
                            subtitle_align="center",
                            padding=(0, 1),
                            width=panel_width
                        ),
                        Panel(
                            right_panel or "",
                            title="[green]Modified Content[/green]",
                            title_align="center",
                            subtitle=str(change.name),
                            subtitle_align="center",
                            padding=(0, 1),
                            width=panel_width
                        )
                    ]

                    # Create columns with fixed width panels
                    columns = Columns(panels, equal=True, expand=False)
                    console.print()
                    console.print(columns, justify="center")
                    console.print()
                else:
                    # Vertical layout for narrow terminals
                    panels = [
                        Panel(
                            left_panel or "",
                            title="[red]Original Content[/red]",
                            title_align="center",
                            subtitle=str(change.name),
                            subtitle_align="center",
                            padding=(0, 1),
                            width=term_width - 2
                        ),
                        Panel(
                            right_panel or "",
                            title="[green]Modified Content[/green]",
                            title_align="center",
                            subtitle=str(change.name),
                            subtitle_align="center",
                            padding=(0, 1),
                            width=term_width - 2
                        )
                    ]

                    # Display panels vertically
                    console.print()
                    for panel in panels:
                        console.print(panel, justify="center")
                        console.print()

                # Show separator between sections if not last section
                if i < len(sections) - 1:
                    console.print(Rule(" Section Break ", style="cyan dim", align="center"))

                # Update height after displaying content
                current_height += content_height
    else:
        # For non-text changes, show full content side by side
        sections = find_modified_sections(original_lines, new_lines)
        for i, (orig_section, new_section) in enumerate(sections):
            left_panel = format_content(orig_section, orig_section, new_section, True)
            right_panel = format_content(new_section, orig_section, new_section, False)

            # Calculate content height for full file diff
            content_height = len(orig_section) + len(new_section) + 4  # Account for panels
            current_height = check_pager(console, current_height, content_height)

            # Format content with appropriate width
            left_panel = format_content(orig_section, orig_section, new_section, True)
            right_panel = format_content(new_section, orig_section, new_section, False)

            # Check terminal width for layout decision
            term_width = console.width or 120
            min_panel_width = 60  # Minimum width for readable content

            # Determine if we can do side-by-side layout
            can_do_side_by_side = term_width >= (min_panel_width * 2 + 4)  # +4 for padding

            if not can_do_side_by_side:
                console.print("[yellow]Terminal width is limited. Using vertical layout for better readability.[/yellow]")
                console.print(f"[dim]Recommended terminal width: {min_panel_width * 2 + 4} or greater[/dim]")

            # Create unified header panel
            header_text = Text()
            header_text.append("[red]Original[/red]", style="bold")
            header_text.append(" vs ")
            header_text.append("[green]Modified[/green]", style="bold")
            header_text.append(f" - {change.name}")

            header_panel = Panel(
                header_text,
                box=box.HEAVY,
                style="cyan",
                padding=(0, 1)
            )

            # Create content panels without individual titles
            panels = [
                Panel(
                    left_panel,
                    padding=(0, 1),
                    width=None if can_do_side_by_side else term_width - 2
                ),
                Panel(
                    right_panel,
                    padding=(0, 1),
                    width=None if can_do_side_by_side else term_width - 2
                )
            ]

            # Display unified header
            console.print(header_panel, justify="center")

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
            current_height += content_height

    # Add final separator and success message
    console.print(Rule(title="End Of Changes", style="bold blue"))
    console.print()
    console.print(Panel("[yellow]You're the best! All changes have been previewed successfully![/yellow]",
                       style="yellow",
                       title="Success",
                       title_align="center"))
    console.print()

def find_modified_sections(original: list[str], modified: list[str], context_lines: int = 3) -> list[tuple[list[str], list[str]]]:
    """
    Find modified sections between original and modified text with surrounding context.
    Merges sections with separator lines.

    Args:
        original: List of original lines
        modified: List of modified lines
        context_lines: Number of unchanged context lines to include

    Returns:
        List of tuples containing (original_section, modified_section) line pairs
    """
    # Find different lines
    different_lines = set()
    for i in range(max(len(original), len(modified))):
        if i >= len(original) or i >= len(modified):
            different_lines.add(i)
        elif original[i] != modified[i]:
            different_lines.add(i)

    if not different_lines:
        return []

    # Group differences into sections with context
    sections = []
    current_section = set()

    # Track original and modified content
    orig_content = []
    mod_content = []

    for line_num in sorted(different_lines):
        # If this line is far from current section, start new section
        if not current_section or line_num <= max(current_section) + context_lines * 2:
            current_section.add(line_num)
        else:
            # Process current section
            start = max(0, min(current_section) - context_lines)
            end = min(max(len(original), len(modified)),
                     max(current_section) + context_lines + 1)

            # Add separator if not first section
            if orig_content:
                orig_content.append("...")
                mod_content.append("...")

            # Add section content
            orig_content.extend(original[start:end])
            mod_content.extend(modified[start:end])

            current_section = {line_num}

    # Process final section
    if current_section:
        start = max(0, min(current_section) - context_lines)
        end = min(max(len(original), len(modified)),
                 max(current_section) + context_lines + 1)

        # Add separator if needed
        if orig_content:
            orig_content.append("...")
            mod_content.append("...")

        # Add final section content
        orig_content.extend(original[start:end])
        mod_content.extend(modified[start:end])

    # Return merged content as single section
    return [(orig_content, mod_content)] if orig_content else []

def create_new_file_panel(name: Text, content: Text) -> Panel:
    """Create a panel for new file creation with stats"""
    stats = get_file_stats(content)
    preview = create_content_preview(Path(str(name)), str(content))
    return Panel(
        preview,
        title=f"[green]New File: {name}[/green]",
        title_align="left",
        subtitle=f"[dim]{stats}[/dim]",
        subtitle_align="right",
        box=box.HEAVY
    )

def create_replace_panel(name: Text, change: FileChange) -> Panel:
    """Create a panel for file replacement"""
    original = change.original_content or ""
    new_content = change.content or ""
    
    term_width = Console().width or 120
    panel_width = max(60, (term_width - 10) // 2)
    
    panels = [
        Panel(
            format_content(original.splitlines(), original.splitlines(), new_content.splitlines(), True),
            title="[red]Original Content[/red]",
            title_align="left",
            width=panel_width
        ),
        Panel(
            format_content(new_content.splitlines(), original.splitlines(), new_content.splitlines(), False),
            title="[green]New Content[/green]",
            title_align="left",
            width=panel_width
        )
    ]
    
    return Panel(Columns(panels), title=f"[yellow]Replace: {name}[/yellow]", box=box.HEAVY)

def create_remove_file_panel(name: Text) -> Panel:
    """Create a panel for file removal"""
    return Panel(
        "[red]This file will be removed[/red]",
        title=f"[red]Remove File: {name}[/red]",
        title_align="left",
        box=box.HEAVY
    )

def create_change_panel(search_content: Text, replace_content: Text, description: Text, width: int) -> Panel:
    """Create a panel for text modifications"""
    search_lines = search_content.splitlines() if search_content else []
    replace_lines = replace_content.splitlines() if replace_content else []
    
    term_width = Console().width or 120
    panel_width = max(60, (term_width - 10) // width)
    
    panels = [
        Panel(
            format_content(search_lines, search_lines, replace_lines, True),
            title="[red]Search Content[/red]",
            title_align="left",
            width=panel_width
        ),
        Panel(
            format_content(replace_lines, search_lines, replace_lines, False),
            title="[green]Replace Content[/green]",
            title_align="left",
            width=panel_width
        )
    ]
    
    return Panel(
        Columns(panels),
        title=f"[blue]Modification: {description}[/blue]",
        box=box.HEAVY
    )
def show_delete_panel(console: Console, change: FileChange, change_index: int = 0, total_changes: int = 1) -> None:
    """Show a specialized panel for file deletion operations

    Args:
        console: Rich console instance
        change: FileChange object containing the changes
        change_index: Current change number (0-based)
        total_changes: Total number of changes
    """
    # Track content height for panel display
    current_height = 0

    # Show the header with reason and progress
    operation = change.operation.name.replace('_', ' ').title()
    progress = f"Change {change_index + 1}/{total_changes}"

    # Create centered reason text if present
    reason_text = Text()
    if change.reason:
        reason_text.append("\n")
        reason_text.append(change.reason, style="italic")

    # Build header with operation and progress
    header = Text()
    header.append(f"{operation}:", style="bold red")
    header.append(f" {change.name} ")
    header.append(f"({progress})", style="dim")
    header.append(reason_text)

    # Display panel with centered content
    console.print(Panel(header, box=box.HEAVY, style="red", title_align="center"))

    # Create deletion panel
    delete_text = Text()
    delete_text.append("This file will be removed", style="bold red")
    if change.original_content:
        delete_text.append("\n\nOriginal file path: ", style="dim")
        delete_text.append(str(change.name), style="red")

    console.print(Panel(
        delete_text,
        title="[red]File Deletion[/red]",
        title_align="center",
        border_style="red",
        padding=(1, 2)
    ))

    # Add final separator
    console.print(Rule(title="End Of Changes", style="bold red"))
    console.print()
import os
from typing import Union

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