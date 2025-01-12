from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from pathlib import Path

# Constants for panel layout
PANEL_MIN_WIDTH = 40
PANEL_MAX_WIDTH = 120  # Maximum width for a single column
PANEL_PADDING = 4
COLUMN_SPACING = 2
from rich.columns import Columns
from rich import box
from rich.text import Text
from rich.syntax import Syntax
from typing import List, Union, Tuple
from ..models import FileChange, ChangeOperation
from .styling import format_content, create_legend_items
from .content import create_content_preview, get_file_syntax
from .sections import find_modified_sections
from rich.rule import Rule
from pathlib import Path
import shutil
import sys


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

    # Left-aligned change number
    progress = f"Change {current}/{total}"
    header.append(progress, style="bold blue")

    # Center-aligned filename
    header.append(" │ ", style="dim")
    header.append(str(filename), style="bold white")

    # Right-aligned reason if provided
    if reason:
        header.append(" │ ", style="dim")
        header.append(reason, style="yellow")

    return header

def preview_all_changes(console: Console, changes: List[FileChange]) -> None:
    """Show a summary of all changes with side-by-side comparison."""
    total_changes = len(changes)
    legend_shown = False

    console.print("[yellow]Starting changes preview...[/yellow]", justify="center")
    console.print()

    # Group changes by operation type
    grouped_changes = {}
    for change in changes:
        if change.operation not in grouped_changes:
            grouped_changes[change.operation] = []
        grouped_changes[change.operation].append(change)

    # First show file operations (create, remove, rename, move)
    _show_file_operations(console, grouped_changes)

    for i, change in enumerate(changes):
        if change.operation in (ChangeOperation.REPLACE_FILE, ChangeOperation.MODIFY_FILE):
            legend_shown = show_side_by_side_diff(console, change, i, total_changes, legend_shown)

    # Show final success message with enhanced visibility
    console.print()
    success_text = Text("🎉 All changes have been previewed successfully! 🎉", style="bold green")
    console.print(Panel(
        success_text,
        box=box.ROUNDED,
        style="green",
        padding=(1, 2)
    ), justify="center")
    console.print()

def _show_file_operations(console: Console, grouped_changes: dict) -> None:
    """Display file operation summaries with content preview for new files."""
    # Show file creations first
    if ChangeOperation.CREATE_FILE in grouped_changes:
        for change in grouped_changes[ChangeOperation.CREATE_FILE]:
            console.print(Rule(f"[green]Creating new file: {change.name}[/green]", style="green"), justify="center")
            if change.content:
                preview = create_content_preview(Path(change.name), change.content, is_new=True)
                console.print(preview, justify="center")
            console.print()

    # Show file and directory removals
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

def calculate_panel_widths(left_content: str, right_content: str, term_width: int) -> Tuple[int, int]:
    """Calculate optimal widths for side-by-side panels with overflow protection."""
    # Reserve space for padding and spacing
    available_width = term_width - PANEL_PADDING - COLUMN_SPACING

    # Calculate maximum content widths
    left_max = max((len(line) for line in left_content.splitlines()), default=0)
    right_max = max((len(line) for line in right_content.splitlines()), default=0)

    # Ensure minimum width requirements
    left_max = max(PANEL_MIN_WIDTH, min(left_max, PANEL_MAX_WIDTH))
    right_max = max(PANEL_MIN_WIDTH, min(right_max, PANEL_MAX_WIDTH))

    # If total width exceeds available space, scale proportionally
    total_width = left_max + right_max
    if total_width > available_width:
        ratio = left_max / total_width
        left_width = max(PANEL_MIN_WIDTH, min(PANEL_MAX_WIDTH, int(available_width * ratio)))
        right_width = max(PANEL_MIN_WIDTH, min(PANEL_MAX_WIDTH, available_width - left_width))
    else:
        left_width = left_max
        right_width = right_max

    # If content fits within available width, use constrained sizes
    total_width = left_max + right_max
    if total_width <= available_width:
        return left_max, right_max

    # Otherwise distribute proportionally while respecting min/max constraints
    ratio = left_max / (total_width or 1)
    left_width = min(
        PANEL_MAX_WIDTH,
        max(PANEL_MIN_WIDTH, int(available_width * ratio))
    )
    right_width = min(
        PANEL_MAX_WIDTH,
        max(PANEL_MIN_WIDTH, available_width - left_width)
    )

    return left_width, right_width

def create_diff_panels(orig_section: List[str], new_section: List[str], filename: str,
                      can_do_side_by_side: bool, term_width: int) -> List[Panel]:
    # Detect if file is Python
    is_python = filename.endswith('.py')
    syntax_type = 'python' if is_python else None

    # Calculate optimal widths
    left_width, right_width = calculate_panel_widths(
        '\n'.join(orig_section), '\n'.join(new_section), term_width
    )
    """Create panels for side-by-side diff view with optimal widths and syntax highlighting"""
    # Get syntax type using centralized function
    syntax_type = get_file_syntax(Path(filename))

    # Format content with or without syntax highlighting and enforce word wrapping
    if syntax_type:
        left_content = Syntax('\n'.join(orig_section), syntax_type, theme="monokai",
                             line_numbers=True, word_wrap=True, code_width=left_width)
        right_content = Syntax('\n'.join(new_section), syntax_type, theme="monokai",
                              line_numbers=True, word_wrap=True, code_width=right_width)
    else:
        left_content = format_content(orig_section, orig_section, new_section, True,
                                     syntax_type=syntax_type)
        right_content = format_content(new_section, orig_section, new_section, False,
                                      syntax_type=syntax_type)

    # Calculate optimal widths using dedicated function
    left_width, right_width = calculate_panel_widths(
        str(left_content), str(right_content), term_width
    )

    # Create panels with calculated widths
    panels = [
        Panel(left_content, title="[red]Original[/red]", title_align="center", width=left_width),
        Panel(right_content, title="[green]Modified[/green]", title_align="center", width=right_width)
    ]

    return panels

def show_side_by_side_diff(console: Console, change: FileChange, change_index: int = 0, 
                          total_changes: int = 1, legend_shown: bool = False) -> bool:
    """Show side-by-side diff panels for a file change with progress tracking and reason
    
    Returns:
        bool: Whether the legend was shown during this call
    """
    term_width = console.width or 120
    min_panel_width = 40
    can_do_side_by_side = term_width >= (min_panel_width * 2 + 4)

    if change.operation == ChangeOperation.REMOVE_FILE:
        show_delete_panel(console, change, change_index, total_changes)
        return False

    original = change.original_content or ""
    new_content = change.content or ""

    if original and original == new_content:
        print("Unexpected empty change", change)
        return False

    original_lines = original.splitlines()
    new_lines = new_content.splitlines()

    # Create and display header
    operation = change.operation.name.replace('_', ' ').title()
    header = create_progress_header(operation, change.name, change_index + 1, total_changes, change.reason)
    console.print(Panel(Text.assemble(header, justify="center"), box=box.HEAVY, style="cyan", title_align="center"))

    def create_diff_columns(orig_section: List[str], new_section: List[str],
                           change_name: str, can_do_side_by_side: bool, term_width: int) -> List[Text]:
        """Create balanced columns for side-by-side diff view with optimal widths"""
        left_content = format_content(orig_section, orig_section, new_section, True)
        right_content = format_content(new_section, orig_section, new_section, False)
    
        # Skip empty modified content
        if not any(new_section):
            return [left_content]
    
        if can_do_side_by_side:
            # Use dedicated function to calculate widths
            left_width, right_width = calculate_panel_widths(
                str(left_content), str(right_content), term_width
            )
        else:
            left_width = right_width = term_width - PANEL_PADDING
    
        # Create headers with column-specific widths
        def create_column_header(text: str, width: int, style: str) -> Text:
            header = Text()
            text_len = len(text)
            padding = 2
    
            # Calculate decoration width to fit column width
            avail_width = width - (padding * 2) - text_len
            left_deco = avail_width // 2
            right_deco = avail_width - left_deco
    
            if left_deco > 0:
                header.append("─" * left_deco, style=style)
            header.append(" " * padding + text + " " * padding, style=style)
            if right_deco > 0:
                header.append("─" * right_deco, style=style)
    
            # Ensure header fits column width
            while len(str(header)) > width:
                if left_deco > 0:
                    left_deco -= 1
                if right_deco > 0:
                    right_deco -= 1
                header = Text()
                if left_deco > 0:
                    header.append("─" * left_deco, style=style)
                header.append(" " * padding + text + " " * padding, style=style)
                if right_deco > 0:
                    header.append("─" * right_deco, style=style)
    
            return header
    
        # Create headers with proper widths
        left_header = create_column_header("Original", left_width, "red bold")
        right_header = create_column_header("Modified", right_width, "green bold")
    
        # Combine headers with content
        left_column = Text()
        left_column.append(left_header)
        left_column.append("\n")  # Add spacing after header
        left_column.append(left_content)

        right_column = Text()
        right_column.append(right_header)
        right_column.append("\n")  # Add spacing after header
        right_column.append(right_content)
    
        return [left_column, right_column]

    # Handle text changes
    if change.text_changes:
        # Show legend before first text operation if not shown yet
        if not legend_shown:
            console.print()
            console.print(create_legend_items(console), justify="center")
            console.print()
            legend_shown = True

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
                columns = create_diff_columns(orig_section, new_section, change.name,
                                             can_do_side_by_side, term_width)

                if can_do_side_by_side:
                    console.print(Columns(columns, equal=True, expand=False), justify="center")
                else:
                    console.print()
                    for column in columns:
                        console.print(column, justify="center")
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
                # Use balanced column widths
                available_width = console.width
                left_content = str(panels[0].renderable)
                right_content = str(panels[1].renderable) if len(panels) > 1 else ""
    
                # Calculate optimal widths
                left_max = max((len(line) for line in left_content.splitlines()), default=0)
                right_max = max((len(line) for line in right_content.splitlines()), default=0)
    
                # Apply balanced width calculation
                total_width = left_max + right_max
                if total_width <= available_width - 4:
                    left_width = left_max
                    right_width = right_max
                else:
                    ratio = left_max / (total_width or 1)
                    left_width = int((available_width - 4) * ratio)
                    right_width = (available_width - 4) - left_width

                # Set panel widths
                panels[0].width = left_width
                if len(panels) > 1:
                    panels[1].width = right_width

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

        # Get syntax type using centralized function
        syntax_type = get_file_syntax(Path(change.name))

        # Calculate optimal width based on content
        content_lines = change.original_content.splitlines()
        max_line_length = max((len(line) for line in content_lines), default=0)
        optimal_width = max(max_line_length + 4, 40)  # 4 chars padding, 40 chars minimum

        syntax = Syntax(
            change.original_content,
            "python",
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
            background_color="red_1",
            code_width=optimal_width
        )
        content.append(str(syntax))

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