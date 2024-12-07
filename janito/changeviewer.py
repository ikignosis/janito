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






def show_changes_legend(console: Console) -> None:
    """Display a legend explaining the colors and symbols used in change previews in a horizontal layout"""
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


def show_change_preview(console: Console, filepath: Path, change: FileChange) -> None:
    """Display a preview of changes for a single file with side-by-side comparison"""
    # Show changes legend first
    show_changes_legend(console)
      
    # Create main file panel content
    main_content = []

    # Handle new file preview
    if change.is_new_file:
        new_file_panel = Panel(
            Text(change.content),
            title="New File Content",
            title_align="left",
            border_style="green",
            box=box.ROUNDED
        )
        main_content.append(new_file_panel)
        
        # Create and display main file panel
        file_panel = Panel(
            Columns(main_content),
            title=str(filepath),
            title_align="left",
            border_style="white",
            box=box.ROUNDED        )
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
        title=f"Modifying {filepath}",
        title_align="left",
        border_style="white",
        box=box.ROUNDED
    )
    console.print(file_panel)
    console.print()

# Remove or comment out the unused unified panel code since we're using direct column display

def preview_all_changes(console: Console, changes: Dict[Path, FileChange]) -> None:
    """Show preview for all file changes"""
    console.print("\n[bold blue]Change Preview[/bold blue]")
    
    for filepath, change in changes.items():
        show_change_preview(console, filepath, change)


def _display_options(options: Dict[str, AnalysisOption]) -> None:
    """Display available options in a centered, responsive layout with consistent spacing."""
    console = Console()
    
    # Display centered header with decorative rule
    console.print()
    console.print(Rule(" Available Options ", style="bold cyan", align="center"))
    console.print()
    
    # Safety check for empty options
    if not options:
        console.print(Panel("[yellow]No options available[/yellow]", border_style="yellow"))
        return
    
    # Calculate optimal layout dimensions based on terminal width
    terminal_width = console.width or 100
    panel_padding = (1, 2)  # Consistent padding for all panels
    available_width = terminal_width - 4  # Account for margins
    
    # Determine optimal panel width and number of columns
    min_panels_per_row = 1
    max_panels_per_row = 3
    optimal_panel_width = min(
        available_width // max_panels_per_row,
        available_width // min_panels_per_row
    )
    
    if optimal_panel_width < MIN_PANEL_WIDTH:
        optimal_panel_width = MIN_PANEL_WIDTH
    
    # Create panels with consistent styling and spacing
    panels = []
    for letter, option in options.items():
        # Build content with consistent formatting
        content = Text()
        
        # Add description section
        content.append("Description:\n", style="bold cyan")
        for item in option.description_items:
            content.append(f"• {item}\n", style="white")
        content.append("\n")
        
        # Add affected files section if present
        if option.affected_files:
            content.append("Affected files:\n", style="bold cyan")
            for file in option.affected_files:
                content.append(f"• {file}\n", style="yellow")
        
        # Create panel with consistent styling
        panel = Panel(
            content,
            box=box.ROUNDED,
            border_style="cyan",
            title=f"Option {letter}: {option.summary}",
            title_align="center",
            padding=panel_padding,
            width=optimal_panel_width
        )
        panels.append(panel)
    
    # Calculate optimal number of columns based on available width
    num_columns = max(1, min(
        len(panels),  # Don't exceed number of panels
        available_width // optimal_panel_width,  # Width-based limit
        max_panels_per_row  # Maximum columns limit
    ))
    
    # Create a centered container panel for all options
    container = Panel(
        Columns(
            panels,
            num_columns=num_columns,
            equal=True,
            align="center",
            padding=(0, 2)  # Consistent spacing between columns
        ),
        box=box.SIMPLE,
        padding=(1, 4),  # Add padding around the columns for better centering
        width=min(terminal_width - 4, num_columns * optimal_panel_width + (num_columns - 1) * 4)
    )

    # Display the centered container
    console.print(Columns([container], align="center"))
    console.print()
