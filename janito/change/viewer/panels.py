from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.syntax import Syntax
from rich.table import Table
from rich import box
from pathlib import Path
from typing import List
from datetime import datetime
from ...change.parser import FileChange, ChangeOperation, TextChange
from janito.config import config
from .styling import format_content, create_legend_items, current_theme
from .themes import ColorTheme

def create_text_modification_panel(change: TextChange) -> Panel:
    """Create a panel showing search/replace text comparison"""
    content_table = Table.grid(padding=(0, 2))
    content_table.add_column("Search Pattern", justify="left")
    content_table.add_column("Replace With", justify="left")

    # Add headers
    content_table.add_row(
        Text("Search Pattern", style="bold cyan"),
        Text("Replace With", style="bold cyan")
    )

    # Format search and replace content
    search_lines = change.search_content.splitlines() if change.search_content else []
    replace_lines = change.replace_content.splitlines() if change.replace_content else []

    content_table.add_row(
        format_content(search_lines, search_lines, replace_lines, True, 'modify'),
        format_content(replace_lines, search_lines, replace_lines, False, 'modify')
    )

    return Panel(
        content_table,
        title=f"Text Modification{' - ' + change.reason if change.reason else ''}",
        border_style="blue"
    )

def _show_legend(console: Console) -> None:
    """Show the unified legend status bar"""
    legend = create_legend_items()
    legend_panel = Panel(
        legend,
        title="Changes Legend",
        title_align="center",
        border_style="white",
        box=box.ROUNDED,
        padding=(0, 2)
    )
    console.print(Columns([legend_panel], align="center", expand=True))
    console.print()

def show_change_preview(console: Console, filepath: Path, change: FileChange) -> None:
    """Display a unified preview of changes for a single file"""
    operation_icons = {
        ChangeOperation.CREATE_FILE: "✨",
        ChangeOperation.REPLACE_FILE: "🔄",
        ChangeOperation.REMOVE_FILE: "🗑️",
        ChangeOperation.MODIFY_FILE: "🔧",
        ChangeOperation.RENAME_FILE: "📝"
    }

    border_styles = {
        ChangeOperation.CREATE_FILE: "#8AE234",
        ChangeOperation.REPLACE_FILE: "#FFB86C",
        ChangeOperation.REMOVE_FILE: "#F44336",
        ChangeOperation.MODIFY_FILE: "#61AFEF",
        ChangeOperation.RENAME_FILE: "#C678DD"
    }

    icon = operation_icons.get(change.operation, "❓")
    border_style = border_styles.get(change.operation, "white")

    # Build content based on operation type
    content = Table.grid(padding=(1, 0))

    if change.operation == ChangeOperation.REMOVE_FILE:
        content.add_row(Text(f"This file will be deleted", style="red"))
    elif change.operation == ChangeOperation.RENAME_FILE:
        content.add_row(Text(f"Renaming from {change.source} to {change.target}"))
    elif change.operation == ChangeOperation.MODIFY_FILE:
        # Show text modifications separately
        for text_change in change.text_changes:
            content.add_row(create_text_modification_panel(text_change))
    else:
        # Add metadata for file operations
        old_size = len(change.original_content.encode('utf-8')) if change.original_content else None
        new_size = len(change.content.encode('utf-8')) if change.content else None
        content.add_row(create_file_metadata_panel(filepath, old_size, new_size))

        # Add content preview for file operations
        if change.operation == ChangeOperation.CREATE_FILE:
            content.add_row(create_content_preview(change.content))
        elif change.operation == ChangeOperation.REPLACE_FILE:
            content.add_row(create_content_preview(
                change.original_content or "",
                change.content,
                change.operation.name.lower()
            ))

    # Create main panel
    operation_name = change.operation.name.title().replace('_', ' ')
    panel = Panel(
        content,
        title=f"[bold]{icon} {operation_name} {filepath}[/bold]",
        title_align="left",
        border_style=border_style,
        box=box.ROUNDED
    )

    console.print(panel)
    console.print()

    # Add spacing after preview
    console.print()

def preview_all_changes(console: Console, changes: List[FileChange]) -> None:
    """Show preview of all changes with unified styling"""
    # Show legend first
    _show_legend(console)

    # Then show all changes
    for change in changes:
        show_change_preview(console, change.name, change)