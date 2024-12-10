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
from janito.fileparser import FileChange
from janito.config import config
from .styling import format_content, create_legend_items, current_theme
from .themes import ColorTheme
from .diff import find_common_sections


def create_new_file_panel(filepath: Path, content: str) -> Panel:
    """Create a panel for new file creation"""
    size_bytes = len(content.encode('utf-8'))
    size_str = f"{size_bytes} bytes" if size_bytes < 1024 else f"{size_bytes/1024:.1f} KB"

    # Create metadata table
    metadata = Table.grid(padding=(0, 1))
    metadata.add_row("File Size:", size_str)
    metadata.add_row("Created:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Create content preview with empty left panel
    content_table = Table.grid(padding=(0, 2))
    content_table.add_column("Before", justify="left")
    content_table.add_column("After", justify="left")

    empty_panel = Panel(
        Text("(No previous content)", style="dim"),
        title="Previous Content",
        title_align="left",
        border_style="#E06C75",
        box=box.ROUNDED
    )

    content_display = content
    if filepath.suffix in ['.py', '.js', '.ts', '.java', '.cpp', '.c']:
        try:
            content_display = Syntax(content, filepath.suffix.lstrip('.'), theme="monokai")
        except:
            pass

    new_panel = Panel(
        content_display,
        title="New Content",
        title_align="left",
        border_style="#61AFEF",
        box=box.ROUNDED
    )

    content_table.add_row(empty_panel, new_panel)
    
    content = Table.grid(padding=(1, 0))
    content.add_row(Panel(metadata, title="File Metadata", border_style="white"))
    content.add_row(Panel(content_table, title="Content Preview", border_style="white"))

    return Panel(
        content,
        title=f"[bold]✨ Creating {filepath}[/bold]",
        title_align="left",
        border_style="#8AE234",
        box=box.ROUNDED
    )

def create_change_panel(search: str, replace: str | None, description: str, index: int) -> Panel:
    """Create a panel for file changes"""
    operation = 'delete' if replace is None else 'modify'
    
    if replace is None:
        return Panel(
            Text(search, style="red"),
            title=f"- Content to Delete{' - ' + description if description else ''}",
            title_align="left",
            border_style="#E06C75",
            box=box.ROUNDED
        )

    search_lines = search.splitlines()
    replace_lines = replace.splitlines()
    common_top, search_middle, replace_middle, common_bottom, all_search_lines = find_common_sections(search_lines, replace_lines)

    content_table = Table.grid(padding=(0, 2))
    content_table.add_column("Current", justify="left", ratio=1)
    content_table.add_column("New", justify="left", ratio=1)
    
    # Add column headers
    content_table.add_row(
        Text("Current Content", style="bold cyan"),
        Text("New Content", style="bold cyan")
    )
    
    # Add the actual content
    content_table.add_row(
        format_content(search_lines, search_lines, replace_lines, True, operation),
        format_content(replace_lines, search_lines, replace_lines, False, operation)
    )

    header = f"Change {index}"
    if description:
        header += f": {description}"

    return Panel(
        content_table,
        title=header,
        title_align="left",
        border_style="cyan",
        box=box.ROUNDED
    )

def create_replace_panel(filepath: Path, change: FileChange) -> Panel:
    """Create a panel for file replacement with metadata"""
    old_size = len(change.original_content.encode('utf-8'))
    new_size = len(change.content.encode('utf-8'))
    
    # Create metadata table
    metadata = Table.grid(padding=(0, 1))
    metadata.add_row("Original Size:", f"{old_size/1024:.1f} KB")
    metadata.add_row("New Size:", f"{new_size/1024:.1f} KB")
    metadata.add_row("Size Change:", f"{(new_size - old_size)/1024:+.1f} KB")
    metadata.add_row("Modified:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Create unified diff preview
    content_table = Table.grid(padding=(0, 2))
    content_table.add_column("Current", justify="left")
    content_table.add_column("New", justify="left")
    
    # Add column headers
    content_table.add_row(
        Text("Current Content", style="bold cyan"),
        Text("New Content", style="bold cyan")
    )
    
    # Add the actual content
    content_table.add_row(
        format_content(change.original_content.splitlines(),
                      change.original_content.splitlines(),
                      change.content.splitlines(), True),
        format_content(change.content.splitlines(),
                      change.original_content.splitlines(),
                      change.content.splitlines(), False)
    )
    
    content = Table.grid(padding=(1, 0))
    content.add_row(Panel(metadata, title="File Metadata", border_style="white"))
    content.add_row(Panel(content_table, title="Content Preview", border_style="white"))
    
    return Panel(
        content,
        title=f"[bold]🔄 Replacing {filepath}[/bold]",
        title_align="left",
        border_style="#FFB86C",
        box=box.ROUNDED
    )

def create_remove_file_panel(filepath: Path) -> Panel:
    """Create a panel for file removal"""
    return Panel(
        Text(f"This file will be deleted", style="red"),
        title=f"[bold]- Removing {filepath}[/bold]",
        title_align="left",
        border_style="#F44336",
        box=box.HEAVY,
        padding=(1, 2)
    )

def show_change_preview(console: Console, filepath: Path, change: FileChange) -> None:
    """Display a preview of changes for a single file"""
    if change.remove_file:
        panel = create_remove_file_panel(filepath)
        console.print(panel)
        console.print()
        return
        
    if change.is_new_file:
        panel = create_new_file_panel(filepath, change.content)
        console.print(panel)
        console.print()
        return

    if change.replace_file:
        panel = create_replace_panel(filepath, change)
        console.print(panel)
        console.print()
        return

    main_content = []
    for i, (search, replace, description) in enumerate(change.search_blocks, 1):
        panel = create_change_panel(search, replace, description, i)
        main_content.append(panel)

    file_panel = Panel(
        Columns(main_content, align="center"),
        title=f"Modifying {filepath} - {change.description}",
        title_align="left",
        border_style="white",
        box=box.ROUNDED
    )
    console.print(file_panel)
    console.print()

def preview_all_changes(console: Console, changes: List[FileChange]) -> None:
    """Show preview for all file changes"""
    if config.debug:
        _print_debug_info(console, changes)

    console.print("\n[bold blue]Change Preview[/bold blue]")
    
    has_modified_files = any(not change.is_new_file for change in changes)
    if has_modified_files:
        _show_legend(console)
    
    new_files = [change for change in changes if change.is_new_file]
    modified_files = [change for change in changes if not change.is_new_file]
    
    for change in new_files:
        show_change_preview(console, change.path, change)
    for change in modified_files:
        show_change_preview(console, change.path, change)

def _print_debug_info(console: Console, changes: List[FileChange]) -> None:
    """Print debug information about file changes"""
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

def _show_legend(console: Console) -> None:
    """Show the unified legend status bar"""
    legend = create_legend_items()
    
    # Calculate panel width based on legend content
    legend_width = len(str(legend)) + 10  # Add padding for borders
    
    legend_panel = Panel(
        legend,
        title="Changes Legend",
        title_align="center",
        border_style="white",
        box=box.ROUNDED,
        padding=(0, 2),
        width=legend_width
    )
    
    # Create a full-width container and center the legend panel
    container = Columns(
        [legend_panel],
        align="center",
        expand=True
    )
    
    console.print(container)
    console.print()
