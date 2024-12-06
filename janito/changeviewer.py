from pathlib import Path
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from typing import List, Optional
from rich import box
from janito.fileparser import FileChange

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
    
    # Create changes panel
    panel_title = "New File Content" if change.is_new_file else "Changes"
    changes_panel = Panel(
        format_sequence_preview(change.change_content),
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

def preview_all_changes(console: Console, changes: dict[Path, FileChange]) -> None:
    """Show preview for all file changes"""
    console.print("\n[bold blue]Change Preview[/bold blue]")
    
    for filepath, change in changes.items():
        show_change_preview(console, filepath, change)