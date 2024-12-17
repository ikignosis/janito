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

def preview_all_changes(console: Console, changes: List[FileChange]) -> None:
    """Show a summary of all changes with side-by-side comparison and progress tracking"""
    total_changes = len(changes)

    # Group changes by operation type
    grouped_changes = {}
    for change in changes:
        if change.operation not in grouped_changes:
            grouped_changes[change.operation] = []
        grouped_changes[change.operation].append(change)

    # Show file operations with rule lines
    for operation, group in grouped_changes.items():
        for change in group:
            if operation == ChangeOperation.CREATE_FILE:
                console.print(Rule(f"[green]Creating new file: {change.name}[/green]", style="green"))
            elif operation == ChangeOperation.REMOVE_FILE:
                console.print(Rule(f"[red]Removing file: {change.name}[/red]", style="red"))
            elif operation == ChangeOperation.RENAME_FILE:
                console.print(Rule(f"[yellow]Renaming file: {change.name} → {change.target}[/yellow]", style="yellow"))

    # Then show side-by-side panels for replacements
    console.print("\n[bold blue]File Changes:[/bold blue]")

    for i, change in enumerate(changes):
        if change.operation in (ChangeOperation.REPLACE_FILE, ChangeOperation.MODIFY_FILE):
            show_side_by_side_diff(console, change, i, total_changes)

def show_side_by_side_diff(console: Console, change: FileChange, change_index: int = 0, total_changes: int = 1) -> None:
    """Show side-by-side diff panels for a file change with progress tracking and reason

    Args:
        console: Rich console instance
        change: FileChange object containing the changes
        change_index: Current change number (0-based)
        total_changes: Total number of changes
    """
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

    # Show compact centered legend
    console.print(create_legend_items(console), justify="center")

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
                console.print(Rule(f" Replace Changes{reason_text} ", style="bold cyan", align="center"))
            elif not text_change.search_content:
                console.print(Rule(f" Append Changes{reason_text} ", style="bold green", align="center"))
            elif not text_change.replace_content:
                console.print(Rule(f" Delete Changes{reason_text} ", style="bold red", align="center"))

            # Format and display each section
            for i, (orig_section, new_section) in enumerate(sections):
                left_panel = format_content(orig_section, orig_section, new_section, True)
                right_panel = format_content(new_section, orig_section, new_section, False)

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
    else:
        # For non-text changes, show full content side by side
        sections = find_modified_sections(original_lines, new_lines)
        for i, (orig_section, new_section) in enumerate(sections):
            left_panel = format_content(orig_section, orig_section, new_section, True)
            right_panel = format_content(new_section, orig_section, new_section, False)

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

            # Create panels with adaptive width
            panels = [
                Panel(
                    left_panel,
                    title="[red]Original Content[/red]",
                    title_align="center",
                    subtitle=str(change.name),
                    subtitle_align="center",
                    padding=(0, 1),
                    width=None if can_do_side_by_side else term_width - 2
                ),
                Panel(
                    right_panel,
                    title="[green]Modified Content[/green]",
                    title_align="center",
                    subtitle=str(change.name),
                    subtitle_align="center",
                    padding=(0, 1),
                    width=None if can_do_side_by_side else term_width - 2
                )
            ]

            # Render panels based on layout
            if can_do_side_by_side:
                # Create centered columns with fixed width
                available_width = console.width
                panel_width = (available_width - 4) // 2  # Account for padding
                for panel in panels:
                    panel.width = panel_width

                columns = Columns(panels, equal=True, expand=False)  # Removed justify parameter
                console.print(columns, justify="center")
            else:
                for panel in panels:
                    console.print(panel, justify="center")
                    console.print()  # Add spacing between panels

            # Show separator between sections if not last section
            if i < len(sections) - 1:
                console.print(Rule(style="dim"))

    # Add final separator after all changes
    console.print(Rule(title="End Of Changes", style="bold blue"))
    console.print()

def find_modified_sections(original: list[str], modified: list[str], context_lines: int = 3) -> list[tuple[list[str], list[str]]]:
    """
    Find modified sections between original and modified text with surrounding context.
    
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
    
    for line_num in sorted(different_lines):
        # If this line is far from current section, start new section
        if not current_section or line_num <= max(current_section) + context_lines * 2:
            current_section.add(line_num)
        else:
            # Process current section
            start = max(0, min(current_section) - context_lines)
            end = min(max(len(original), len(modified)), 
                     max(current_section) + context_lines + 1)
                     
            orig_section = original[start:end]
            mod_section = modified[start:end]
            
            sections.append((orig_section, mod_section))
            current_section = {line_num}
    
    # Process final section
    if current_section:
        start = max(0, min(current_section) - context_lines) 
        end = min(max(len(original), len(modified)),
                 max(current_section) + context_lines + 1)
                 
        orig_section = original[start:end]
        mod_section = modified[start:end]
        
        sections.append((orig_section, mod_section))
        
    return sections

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
    # Show compact centered legend
    console.print(create_legend_items(console), justify="center")

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