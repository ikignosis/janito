from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from pathlib import Path
from typing import List, Union, Tuple
from janito.file_operations import (
    CreateFile, DeleteFile, RenameFile, ReplaceFile, ModifyFile,
    ChangeType
)
from .styling import format_content, create_legend_items
from .content import create_content_preview, get_file_syntax
from .sections import find_modified_sections
from rich.rule import Rule
import shutil
import sys
from rich.columns import Columns
from rich import box
from rich.text import Text
from rich.layout import Layout

# Constants for panel layout
PANEL_MIN_WIDTH = 40
PANEL_MAX_WIDTH = 120  # Maximum width for a single column
PANEL_PADDING = 4
COLUMN_SPACING = 2

def create_progress_header(operation: str, filename: str, current: int, total: int,
                          file_ops: int = 0, reason: str = None) -> Text:
    """Create a compact single-line header with balanced layout.

    Args:
        operation: Type of operation being performed
        filename: Name of the file being modified
        current: Current change number
        total: Total number of changes
        file_ops: Number of file operations (if any)
        reason: Optional reason for the change
    """
    header = Text()

    # Left-aligned change number with file ops if present
    progress = format_change_progress(current, total, file_ops)
    header.append(progress, style="bold blue")

    # Center-aligned filename
    header.append(" │ ", style="dim")
    header.append(str(filename), style="bold white")

    # Right-aligned reason if provided
    if reason:
        header.append(" │ ", style="dim")
        header.append(reason, style="yellow")

    return header

FileOperationType = Union[CreateFile, DeleteFile, RenameFile, ReplaceFile, ModifyFile]

def preview_all_changes(changes: List[FileOperationType]) -> None:
    """Show a summary of all changes with side-by-side comparison."""
    console = Console()
    file_ops, content_changes = count_total_changes(changes)
    total_changes = content_changes
    legend_shown = False

    console.print("[yellow]Starting changes preview...[/yellow]", justify="center")
    if file_ops:
        console.print(f"[yellow]Total changes: {content_changes} content changes + {file_ops} file operations[/yellow]", justify="center")
    console.print()

    # Group changes by type
    create_files = []
    delete_files = []
    rename_files = []
    replace_files = []
    modify_files = []

    for change in changes:
        if isinstance(change, CreateFile):
            create_files.append(change)
        elif isinstance(change, DeleteFile):
            delete_files.append(change)
        elif isinstance(change, RenameFile):
            rename_files.append(change)
        elif isinstance(change, ReplaceFile):
            replace_files.append(change)
        elif isinstance(change, ModifyFile):
            modify_files.append(change)

    # Show file creations first
    if create_files:
        for change in create_files:
            console.print(Rule(f"[green]Creating new file: {change.name}[/green]", style="green"), justify="center")
            if hasattr(change, 'content'):
                preview = create_content_preview(Path(change.name), change.content, is_new=True)
                console.print(preview, justify="center")
            console.print()

    # Show file removals
    if delete_files:
        console.print("\n[bold red]File Removals:[/bold red]")
        for change in delete_files:
            show_delete_panel(console, change, change_index, total_changes)
            change_index += 1
            console.print()

    # Show file renames
    if rename_files:
        console.print("\n[bold yellow]File Renames:[/bold yellow]")
        for change in rename_files:
            console.print(Rule(f"[yellow]Renaming file: {change.name} → {change.new_name}[/yellow]", style="yellow"))
            console.print()

    # Show file replacements
    if replace_files:
        console.print("\n[bold magenta]File Replacements:[/bold magenta]")
        for change in replace_files:
            console.print(Rule(f"[magenta]Replacing content in: {change.name}[/magenta]", style="magenta"))
            preview = create_content_preview(Path(change.name), change.content, is_new=False)
            console.print(preview, justify="center")
            console.print()

    # Show content modifications
    change_index = 0
    total_changes = len(modify_files)
    for modify_change in modify_files:
        # Show header for the file being modified
        console.print(Rule(f"[cyan]Modifying file: {modify_change.name}[/cyan]", style="cyan"))
        
        for content_change in modify_change.get_changes():
            # Get the content based on change type
            if content_change.change_type in (ChangeType.REPLACE, ChangeType.APPEND, ChangeType.INSERT):
                orig_lines = content_change.original_content
                new_lines = content_change.new_content
            elif content_change.change_type == ChangeType.DELETE:
                orig_lines = content_change.original_content
                new_lines = []  # Empty list for deletions
            else:
                raise NotImplementedError(f"Unsupported change type: {content_change.change_type}")

            # Show the diff
            legend_shown = show_side_by_side_diff(
                console,
                modify_change.name,
                orig_lines,
                new_lines,
                change_index,
                total_changes,
                legend_shown,
                f"Lines {content_change.start_line + 1}-{content_change.end_line}",
                file_ops
            )
            change_index += 1
            console.print()  # Add spacing between changes

    # Show final success message
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

def create_side_by_side_columns(orig_section: List[str], new_section: List[str], filename: str,
                           can_do_side_by_side: bool, term_width: int) -> Columns:
    """Create side-by-side diff view using Columns with consistent styling"""
    # Get syntax type using centralized function
    syntax_type = get_file_syntax(Path(filename))

    # Calculate max line widths for each section
    left_max_width = max((len(line) for line in orig_section), default=0)
    right_max_width = max((len(line) for line in new_section), default=0)

    # Add some padding for the titles
    left_max_width = max(left_max_width, len("Original") + 2)
    right_max_width = max(right_max_width, len("Modified") + 2)

    # Calculate optimal widths while respecting max line widths
    total_width = term_width - 4  # Account for padding
    if can_do_side_by_side:
        # Use actual content widths, but ensure they fit in available space
        available_width = total_width - 2  # Account for column spacing
        if (left_max_width + right_max_width) > available_width:
            # Scale proportionally if content is too wide
            ratio = left_max_width / (left_max_width + right_max_width)
            left_width = min(left_max_width, int(available_width * ratio))
            right_width = min(right_max_width, available_width - left_width)
        else:
            left_width = left_max_width
            right_width = right_max_width
    else:
        left_width = right_width = total_width

    # Format content with calculated widths
    left_content = format_content(orig_section, orig_section, new_section, True,
                                width=left_width, syntax_type=syntax_type)
    right_content = format_content(new_section, orig_section, new_section, False,
                                width=right_width, syntax_type=syntax_type)

    # Create text containers with centered titles
    left_text = Text()
    title_padding = (left_width - len("Original")) // 2
    left_text.append(" " * title_padding + "Original" + " " * title_padding, style="red bold")
    left_text.append("\n")
    left_text.append(left_content)

    right_text = Text()
    title_padding = (right_width - len("Modified")) // 2
    right_text.append(" " * title_padding + "Modified" + " " * title_padding, style="green bold")
    right_text.append("\n")
    right_text.append(right_content)

    # Calculate padding for centering the entire columns
    content_width = left_width + right_width + 2  # +2 for column spacing
    side_padding = " " * ((term_width - content_width) // 2)

    # Create centered columns
    return Columns(
        [
            Text(side_padding),
            left_text,
            right_text,
            Text(side_padding)
        ],
        equal=False,
        expand=False,
        padding=(0, 1)
    )

def show_side_by_side_diff(
    console: Console,
    filename: str,
    original_content: List[str],
    new_content: List[str],
    change_index: int = 0,
    total_changes: int = 1,
    legend_shown: bool = False,
    reason: str = None,
    file_ops: int = 0
) -> bool:
    """Show side-by-side diff using Columns for better alignment

    Args:
        console: Rich console instance
        filename: Name of the file being modified
        original_content: Original content lines
        new_content: Modified content lines
        change_index: Current change number (0-based)
        total_changes: Total number of changes
        legend_shown: Whether the legend has been shown
        reason: Optional reason for the change
        file_ops: Number of file operations (default: 0)

    Returns:
        bool: Whether the legend was shown during this call
    """
    term_width = console.width or 120
    min_panel_width = 40
    can_do_side_by_side = term_width >= (min_panel_width * 2 + 4)

    # Create and display header
    header = create_progress_header("Modify", filename, change_index + 1, total_changes,
                                   file_ops=file_ops, reason=reason)
    console.print(Panel(Text.assemble(header, justify="center"), box=box.HEAVY, style="cyan", title_align="center"))

    # Show legend before first text operation if not shown yet
    if not legend_shown:
        console.print()
        console.print(create_legend_items(console), justify="center")
        console.print()
        legend_shown = True

    # Find modified sections
    sections = find_modified_sections(original_content, new_content)

    # Format and display each section
    for i, (orig_section, new_section) in enumerate(sections):
        # Create side-by-side view using columns
        layout = create_side_by_side_columns(
            orig_section,
            new_section,
            filename,
            can_do_side_by_side,
            term_width
        )

        console.print(layout)

        # Show separator between sections if not last section
        if i < len(sections) - 1:
            console.print(Rule(style="dim"))

    return legend_shown

def show_delete_panel(
    console: Console, 
    delete_op: DeleteFile,
    change_index: int = 0, 
    total_changes: int = 1
) -> None:
    """Show an enhanced panel for file deletion operations with status indicators

    Args:
        console: Rich console instance
        delete_op: DeleteFile operation instance
        change_index: Current change number (0-based)
        total_changes: Total number of changes
    """
    header = create_progress_header(
        "Delete",
        delete_op.name,
        change_index + 1,
        total_changes
    )
    header.rstrip()  # Remove trailing newlines

    # Create content text with status indicators
    content = Text()
    content.append("⚠️  ", style="bold yellow")  # Warning icon
    content.append("This file will be permanently removed", style="bold red")
    content.append("\n\n")
    content.append("Status: ", style="bold")
    content.append("Pending Removal", style="red")

    # Show file preview if file exists
    if Path(delete_op.name).exists():
        content.append("\n\n")
        content.append("Original Content Preview:", style="dim red")
        content.append("\n")

        # Get syntax type using centralized function
        syntax_type = get_file_syntax(Path(delete_op.name))

        # Read current file content
        file_content = Path(delete_op.name).read_text()
        
        # Calculate optimal width based on content
        content_lines = file_content.splitlines()
        max_line_length = max((len(line) for line in content_lines), default=0)
        optimal_width = max(max_line_length + 4, 40)  # 4 chars padding, 40 chars minimum

        syntax = Syntax(
            file_content,
            syntax_type,
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

def count_total_changes(changes: List[FileOperationType]) -> Tuple[int, int]:
    """Count total file operations and content changes

    Returns:
        Tuple of (file_operations, content_changes)
    """
    file_ops = 0
    content_changes = 0

    for change in changes:
        if isinstance(change, ModifyFile):
            content_changes += len(change.get_changes())
        else:
            file_ops += 1

    return file_ops, content_changes

def format_change_progress(current: int, total: int, file_ops: int = 0) -> str:
    """Format change progress with optional file operations count

    Args:
        current: Current change number
        total: Total number of changes
        file_ops: Number of file operations (if any)
    """
    if file_ops:
        return f"Change {current}/{total} (+ {file_ops} file operations)"
    return f"Change {current}/{total}"

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
