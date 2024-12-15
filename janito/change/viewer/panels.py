from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich import box
from rich.text import Text
from typing import List
from ..parser import FileChange, ChangeOperation
from .styling import format_content, create_legend_items
from rich.rule import Rule

def preview_all_changes(console: Console, changes: List[FileChange]) -> None:
    """Show a summary of all changes with side-by-side comparison for replacements"""
    console.print("\n[bold blue]Change Operations Summary:[/bold blue]")

    # First show summary
    for change in changes:
        operation = change.operation.name.replace('_', ' ').title()
        path = change.target if change.operation == ChangeOperation.RENAME_FILE else change.name

        if change.operation == ChangeOperation.RENAME_FILE:
            console.print(f"[yellow]• {operation}:[/yellow] {change.name} → {change.target}")
        else:
            console.print(f"[yellow]• {operation}:[/yellow] {path}")

    # Then show side-by-side panels for replacements
    console.print("\n[bold blue]File Replacements:[/bold blue]")

    for change in changes:
        if change.operation in (ChangeOperation.REPLACE_FILE, ChangeOperation.MODIFY_FILE):
            show_side_by_side_diff(console, change)

def show_side_by_side_diff(console: Console, change: FileChange) -> None:
    """Show side-by-side diff panels for a file change"""
    # Get original and new content
    original = change.original_content or ""
    new_content = change.content or ""

    # Split into lines
    original_lines = original.splitlines()
    new_lines = new_content.splitlines()

    # Find modified sections with context
    sections = find_modified_sections(original_lines, new_lines, context_lines=3)

    # Always show the header
    operation = change.operation.name.replace('_', ' ').title()
    header = f"[bold blue]{operation}:[/bold blue] {change.name}"
    console.print(Panel(header, box=box.HEAVY, style="blue"))

    if not sections:
        # If no differences found, show full content side by side
        left_panel = format_content(original_lines, original_lines, new_lines, True)
        right_panel = format_content(new_lines, original_lines, new_lines, False)
        sections = [(original_lines, new_lines)]
    
    # Create panels for each modified section
    for i, (orig_section, new_section) in enumerate(sections):
        # Format content with styling
        left_panel = format_content(orig_section, orig_section, new_section, True)
        right_panel = format_content(new_section, orig_section, new_section, False)

        # Create panels with enhanced titles
        # Calculate panel width based on terminal width
        term_width = console.width or 120
        panel_width = max(60, (term_width - 10) // 2)  # -10 for padding

        left = Panel(
            left_panel,
            title=f"[red]Original Content[/red]",
            title_align="left",
            subtitle=str(change.name),
            subtitle_align="right",
            width=panel_width,
            padding=(0, 1)
        )
        right = Panel(
            right_panel,
            title=f"[green]Modified Content[/green]",
            title_align="left",
            subtitle=str(change.name),
            subtitle_align="right",
            width=panel_width,
            padding=(0, 1)
        )

        # Show panels side by side
        console.print(Columns([left, right]))

        # Show separator between sections
        if i < len(sections) - 1:
            console.print(Rule(style="dim"))

    # Show legend at the end
    console.print(create_legend_items())
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
