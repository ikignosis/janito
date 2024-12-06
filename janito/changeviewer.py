from pathlib import Path
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule  # Add this import
from typing import List, Optional, Dict
from rich import box
from janito.fileparser import FileChange
from janito.analysis import AnalysisOption  # Add this import
from rich.columns import Columns  # Add this import at the top with other imports

MIN_COLUMN_WIDTH = 60  # Minimum width for each column
MIN_PANEL_WIDTH = 40   # Minimum width for each panel

def format_sequence_preview(lines: List[str]) -> Text:
    """Format a sequence of prefixed lines into rich text with colors"""
    text = Text()
    last_was_empty = False
    
    for line in lines:
        if not line:
            # Preserve empty lines but don't duplicate them
            if not last_was_empty:
                text.append("\n")
            last_was_empty = True
            continue
        
        last_was_empty = False
        prefix = line[0] if line[0] in ('=', '>', '<') else ' '
        content = line[1:] if line[0] in ('=', '>', '<') else line
        
        if prefix == '=':
            text.append(f" {content}\n", style="dim")
        elif prefix == '>':
            text.append(f"+{content}\n", style="green")
        elif prefix == '<':
            text.append(f"-{content}\n", style="red")
        else:
            text.append(f" {content}\n", style="yellow dim")
    
    return text

def show_change_preview(console: Console, filepath: Path, change: FileChange) -> None:
    """Display a preview of changes for a single file"""
    # Create file info table
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_row("File:", Text(str(filepath), style="cyan"))
    info_table.add_row("Type:", Text("New file" if change.is_new_file else "Modified", style="yellow"))
    info_table.add_row("Description:", Text(change.description, style="italic"))
    
    # Create file info panel
    info_panel = Panel(
        info_table,
        title="File Information",
        title_align="left",
        border_style="blue",
        box=box.ROUNDED
    )
    
    # Create changes preview panel
    if change.is_new_file:
        content = Text(change.content)
        panel_title = "New File Content"
    else:
        content = Text()
        for i, (search, replace) in enumerate(change.search_blocks, 1):
            content.append(f"\nChange {i}:\n", style="bold cyan")
            if replace is None:
                content.append("Delete:\n", style="red")
                content.append(search, style="red")
            else:
                content.append("Search:\n", style="yellow")
                content.append(f"{search}\n", style="yellow")
                content.append("Replace with:\n", style="green")
                content.append(f"{replace}\n", style="green")
        panel_title = "Changes"
    
    changes_panel = Panel(
        content,
        title=panel_title,
        title_align="left",
        border_style="blue",
        box=box.ROUNDED
    )
    
    # Print panels with spacing
    console.print("\n")
    console.print(info_panel)
    console.print()
    console.print(changes_panel)
    console.print()

def preview_all_changes(console: Console, changes: Dict[Path, FileChange]) -> None:
    """Show preview for all file changes"""
    console.print("\n[bold blue]Change Preview[/bold blue]")
    
    for filepath, change in changes.items():
        show_change_preview(console, filepath, change)

def _display_options(options: Dict[str, AnalysisOption]) -> None:
    """Display available options in a multi-column layout."""
    console = Console()
    
    # Display header
    console.print()
    console.print(Rule(" Available Options ", style="bold cyan", align="center"))
    console.print()
    
    # Safety check for empty options
    if not options:
        console.print("[yellow]No options available[/yellow]")
        return
    
    # Create list of panels without width constraints
    panels = []
    for letter, option in options.items():
        content = Text()
        content.append("Description:\n", style="bold cyan")
        content.append(f"{option.description}\n\n", style="white")
        
        if option.affected_files:
            content.append("Affected files:\n", style="bold cyan")
            for file in option.affected_files:
                content.append(f"• {file}\n", style="yellow")
        
        panels.append(Panel(
            content,
            box=box.ROUNDED,
            border_style="cyan",
            title=f"Option {letter}: {option.summary}",
            title_align="center"
        ))
    
    # Calculate layout based on terminal size
    terminal_width = max(MIN_COLUMN_WIDTH, console.width or MIN_COLUMN_WIDTH)
    
    # For very narrow terminals, display one panel per line
    if terminal_width < MIN_COLUMN_WIDTH * 2:
        for panel in panels:
            console.print(panel)
            console.print()
        return
    
    # For wider terminals, use columns
    num_columns = min(
        len(panels),  # Don't exceed number of panels
        max(1, terminal_width // MIN_COLUMN_WIDTH)  # At least 1 column
    )
    
    columns = Columns(
        panels,
        num_columns=num_columns,
        equal=True,
        align="center",
        padding=(0, 1)
    )
    
    console.print(columns)
    console.print()