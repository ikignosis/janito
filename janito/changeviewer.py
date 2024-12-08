from pathlib import Path
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from typing import List, Optional, Dict, Union, Tuple
from rich import box
from janito.fileparser import FileChange
from janito.analysis import AnalysisOption
from rich.columns import Columns
from rich.syntax import Syntax
from janito.config import config  # Add this import

MIN_PANEL_WIDTH = 40   # Minimum width for each panel


def show_change_preview(console: Console, filepath: Path, change: FileChange) -> None:
    """Display a preview of changes for a single file with side-by-side comparison"""
    # Create main file panel content
    main_content = []

    # Handle new file creation with bright green styling
    if change.is_new_file:
        # Calculate file size and format it
        size_bytes = len(change.content.encode('utf-8'))
        if size_bytes < 1024:
            size_str = f"{size_bytes} bytes"
        else:
            size_kb = size_bytes / 1024
            size_str = f"{size_kb:.1f} KB"

        # Create content display with syntax highlighting if possible
        content_display = change.content
        if filepath.suffix in ['.py', '.js', '.ts', '.java', '.cpp', '.c']:
            try:
                content_display = Syntax(change.content, filepath.suffix.lstrip('.'), theme="monokai")
            except:
                pass

        # Create and display main file panel with bright green border
        file_panel = Panel(
            content_display,
            title=f"[bold]✨ Creating {filepath} ({size_str})[/bold]",
            title_align="left",
            border_style="#8AE234",
            box=box.ROUNDED,
            style="bright_green"
        )
        console.print(file_panel)
        console.print()
        return

    

    # For modifications, create side-by-side comparison for each change
    for i, (search, replace, description) in enumerate(change.search_blocks, 1):
        # Show change header with description
        header = f"Change {i}"
        if description:
            header += f": {description}"
        
        if replace is None:
            # For deletions, show single panel with content to be deleted
            change_panel = Panel(
                Text(search, style="red"),
                title=f"Content to Delete{' - ' + description if description else ''}",
                title_align="left",
                border_style="#E06C75",  # Brighter red
                box=box.ROUNDED
            )
            main_content.append(change_panel)
        else:
            # For replacements, show side-by-side panels

            
            # Find common content between search and replace
            search_lines = search.splitlines()
            replace_lines = replace.splitlines()
            
            # Find common lines from top
            common_top = []
            for s, r in zip(search_lines, replace_lines):
                if s == r:
                    common_top.append(s)
                else:
                    break
                    
            # Find common lines from bottom
            search_remaining = search_lines[len(common_top):]
            replace_remaining = replace_lines[len(common_top):]
            
            common_bottom = []
            for s, r in zip(reversed(search_remaining), reversed(replace_remaining)):
                if s == r:
                    common_bottom.insert(0, s)
                else:
                    break
                    
            # Get the unique middle sections
            search_middle = search_remaining[:-len(common_bottom)] if common_bottom else search_remaining
            replace_middle = replace_remaining[:-len(common_bottom)] if common_bottom else replace_remaining
            



            # Format content with highlighting using consistent colors and line numbers


            def format_content(lines: List[str], is_search: bool) -> Text:
                text = Text()
                
                COLORS = {
                    'unchanged': '#98C379',  # Brighter green for unchanged lines
                    'removed': '#E06C75',    # Clearer red for removed lines
                    'added': '#61AFEF',      # Bright blue for added lines
                    'new': '#C678DD',        # Purple for completely new lines
                    'relocated': '#61AFEF'    # Use same blue for relocated lines
                }
                
                # Create sets of lines for comparison
                search_set = set(search_lines)
                replace_set = set(replace_lines)
                common_lines = search_set & replace_set
                new_lines = replace_set - search_set
                relocated_lines = common_lines - set(common_top) - set(common_bottom)

                def add_line(line: str, style: str, prefix: str = " "):
                    # Special handling for icons
                    if style == COLORS['relocated']:
                        prefix = "⇄"
                    elif style == COLORS['removed'] and prefix == "-":
                        prefix = "✕"
                    elif style == COLORS['new'] or (style == COLORS['added'] and prefix == "+"):
                        prefix = "✚"
                    text.append(prefix, style=style)
                    text.append(f" {line}\n", style=style)
                
                # Format common top section
                for line in common_top:
                    add_line(line, COLORS['unchanged'], "=")
                
                # Format changed middle section
                for line in (search_middle if is_search else replace_middle):
                    if line in relocated_lines:
                        add_line(line, COLORS['relocated'], "⇄")
                    elif not is_search and line in new_lines:
                        add_line(line, COLORS['new'], "+")
                    else:
                        style = COLORS['removed'] if is_search else COLORS['added']
                        prefix = "✕" if is_search else "+"
                        add_line(line, style, prefix)
                
                # Format common bottom section
                for line in common_bottom:
                    add_line(line, COLORS['unchanged'], "=")
                
                return text
            


            # Create panels for old and new content without width constraints
            old_panel = Panel(
                format_content(search_lines, True),
                title="Current Content",
                title_align="left",
                border_style="#E06C75",
                box=box.ROUNDED
            )
            
            new_panel = Panel(
                format_content(replace_lines, False),
                title="New Content",
                title_align="left",
                border_style="#61AFEF",
                box=box.ROUNDED
            )

            # Add change panels to main content with auto-fitting columns
            change_columns = Columns([old_panel, new_panel], equal=True, align="center")
            change_panel = Panel(
                change_columns,
                title=header,
                title_align="left",
                border_style="cyan",
                box=box.ROUNDED
            )
            main_content.append(change_panel)
    
    # Create and display main file panel
    file_panel = Panel(
        Columns(main_content, align="center"),
        title=f"Modifying {filepath} - {change.description}",
        title_align="left",
        border_style="white",
        box=box.ROUNDED
    )
    console.print(file_panel)
    console.print()

# Remove or comment out the unused unified panel code since we're using direct column display

def preview_all_changes(console: Console, changes: List[FileChange]) -> None:
    """Show preview for all file changes"""
    if config.debug:
        console.print("\n[blue]Debug: File Changes to Preview:[/blue]")
        for change in changes:
            console.print(f"\n[cyan]File:[/cyan] {change.path}")
            console.print(f"  [yellow]Is New File:[/yellow] {change.is_new_file}")
            console.print(f"  [yellow]Description:[/yellow] {change.description}")
            if change.search_blocks:
                console.print("  [yellow]Search Blocks:[/yellow]")
                for i, (search, replace, desc) in enumerate(change.search_blocks, 1):
                    console.print(f"    Block {i}:")
                    console.print(f"      Description: {desc or 'No description'}")
                    console.print(f"      Operation: {'Replace' if replace else 'Delete'}")
                    console.print(f"      Search Length: {len(search)} chars")
                    if replace:
                        console.print(f"      Replace Length: {len(replace)} chars")
        console.print("\n[blue]End Debug File Changes[/blue]\n")

    console.print("\n[bold blue]Change Preview[/bold blue]")
    
    # Show legend only if there are modified files
    has_modified_files = any(not change.is_new_file for change in changes)
    if has_modified_files:
        # Create a list of colored text objects
        legend_items = [
            Text("Unchanged", style="#98C379"),
            Text(" • ", style="dim"),
            Text("Removed", style="#E06C75"),
            Text(" • ", style="dim"),
            Text("Relocated", style="#61AFEF"),
            Text(" • ", style="dim"),
            Text("New", style="#C678DD")
        ]
        
        # Combine all items into a single text object
        legend_text = Text()
        for item in legend_items:
            legend_text.append_text(item)
        
        # Create a simple panel with the horizontal legend
        legend_panel = Panel(
            legend_text,
            title="Changes Legend",
            title_align="left",
            border_style="white",
            box=box.ROUNDED,
            padding=(0, 1)
        )
        
        # Center the legend panel horizontally
        console.print(Columns([legend_panel], align="center"))
        console.print()  # Add extra line for spacing
    
    # Show new files first, then modified files
    new_files = [change for change in changes if change.is_new_file]
    modified_files = [change for change in changes if not change.is_new_file]
    
    # Display new files first
    for change in new_files:
        show_change_preview(console, change.path, change)
        
    # Display modified files after
    for change in modified_files:
        show_change_preview(console, change.path, change)



