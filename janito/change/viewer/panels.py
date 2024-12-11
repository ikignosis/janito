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
from ...change.parser import FileChange
from janito.config import config
from .styling import format_content, create_legend_items, current_theme
from .themes import ColorTheme
from .diff import find_common_sections


def create_new_file_panel(filepath: Path, content: str) -> Panel:
    """Create a panel for new file creation"""
    size_bytes = len(content.encode('utf-8'))
    size_str = f"{size_bytes} bytes" if size_bytes < 1024 else f"{size_bytes/1024:.1f} KB"

    # Create metadata table with just file size
    metadata = Table.grid(padding=(0, 4))
    metadata.add_column("File Size", justify="right", style="dim")
    metadata.add_column(justify="left")
    metadata.add_row("File Size:", size_str)

    # Create content display with syntax highlighting if applicable
    content_display = content
    if filepath.suffix in ['.py', '.js', '.ts', '.java', '.cpp', '.c']:
        try:
            content_display = Syntax(content, filepath.suffix.lstrip('.'), theme="monokai")
        except:
            pass

    content_panel = Panel(
        content_display,
        title="New Content",
        title_align="left",
        border_style="#61AFEF",
        box=box.ROUNDED
    )
    
    content = Table.grid(padding=(1, 0))
    content.add_row(Panel(metadata, title="File Metadata", border_style="white"))
    content.add_row(content_panel)

    return Panel(
        content,
        title=f"[bold]✨ Creating {filepath}[/bold]",
        title_align="left",
        border_style="#8AE234",
        box=box.ROUNDED
    )

def create_change_panel(search: str, replace: str | None, description: str, index: int, is_regex: bool = False) -> Panel:
    """Create a panel for file changes"""
    operation = 'delete' if replace is None else 'modify'
    search_type = "regex" if is_regex else "plain text"
    
    if replace is None:
        return Panel(
            Text(search, style="red"),
            title=f"🗑️ Content to Delete [{search_type}]{' - ' + description if description else ''}",
            title_align="left",
            border_style="#E06C75",
            box=box.ROUNDED
        )

    # Split content and find common sections
    search_lines = search.splitlines()
    replace_lines = replace.splitlines()
    content_table = Table.grid(padding=(0, 2))
    content_table.add_column("Current", justify="left", ratio=1)
    content_table.add_column("New", justify="left", ratio=1)
    
    # Add column headers with search type indicator
    content_table.add_row(
        Text(f"Current Content [{search_type}]", style="bold cyan"),
        Text("New Content", style="bold cyan")
    )
    
    # Add the actual content with highlighting
    content_table.add_row(
        format_content(search_lines, search_lines, replace_lines, True, operation),
        format_content(replace_lines, search_lines, replace_lines, False, operation)
    )

    title_emoji = "🔄" if operation == "modify" else "🗑️"
    header = f"{title_emoji} Change {index}"
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
    
    # Create metadata table with horizontal layout
    metadata = Table.grid(padding=(0, 4))
    metadata.add_column("Label", justify="right", style="dim")
    metadata.add_column(justify="left")
    metadata.add_column("Label", justify="right", style="dim")
    metadata.add_column(justify="left")
    metadata.add_column("Label", justify="right", style="dim")
    metadata.add_column(justify="left")
    metadata.add_row(
        "Original Size:", f"{old_size/1024:.1f} KB",
        "New Size:", f"{new_size/1024:.1f} KB",
        "Modified:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

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
    if change.operation == 'remove_file':
        panel = create_remove_file_panel(filepath)
    elif change.operation == 'create_file':
        panel = create_new_file_panel(filepath, change.content)
    elif change.operation == 'replace_file':
        panel = create_replace_panel(filepath, change)
    elif change.operation == 'modify_file':
        main_content = []
        for i, mod in enumerate(change.modifications, 1):
            panel = create_change_panel(
                mod.search_content,
                mod.replace_content,
                change.description,
                i,
                mod.is_regex
            )
            main_content.append(panel)
        panel = Panel(
            Columns(main_content, align="center"),
            title=f"🔧 Modifying {filepath}{' - ' + change.description if change.description else ''}",
            title_align="left",
            border_style="white",
            box=box.ROUNDED
        )

    console.print(panel)
    console.print()

def preview_all_changes(console: Console, changes: List[FileChange]) -> None:
    """Show preview for all file changes"""
    if config.debug:
        _print_debug_info(console, changes)

    console.print("\n[bold blue]📋 Change Preview[/bold blue]")
    
    # Group changes by operation type
    change_groups = {
        'create_file': [], 'modify_file': [], 'replace_file': [],
        'remove_file': [], 'rename_file': []
    }
    
    for change in changes:
        change_groups[change.operation].append(change)
    
    # Show changes in logical order
    if change_groups['create_file']:
        console.print("\n[green]✨ Created Files:[/green]")
        for change in change_groups['create_file']:
            show_change_preview(console, change.path, change)
            
    if change_groups['modify_file']:
        console.print("\n[yellow]🔧 Modified Files:[/yellow]")
        for change in change_groups['modify_file']:
            show_change_preview(console, change.path, change)
            
    if change_groups['replace_file']:
        console.print("\n[yellow]🔄 Replaced Files:[/yellow]")
        for change in change_groups['replace_file']:
            show_change_preview(console, change.path, change)
            
    if change_groups['rename_file']:
        console.print("\n[blue]📝 Renamed Files:[/blue]")
        for change in change_groups['rename_file']:
            console.print(f"  [dim]{change.path}[/dim] → [bold]{change.new_path}[/bold]")
            
    if change_groups['remove_file']:
        console.print("\n[red]🗑️ Removed Files:[/red]")
        for change in change_groups['remove_file']:
            show_change_preview(console, change.path, change)

def _print_debug_info(console: Console, changes: List[FileChange]) -> None:
    """Print debug information about file changes"""
    console.print("\n[blue]🔍 Debug: File Changes Analysis[/blue]")
    
    operations = {'create_file': [], 'modify_file': [], 'replace_file': [], 'remove_file': [], 'rename_file': []}
    for change in changes:
        operations[change.operation].append(change)
        
    for op_type, op_changes in operations.items():
        if not op_changes:
            continue
            
        console.print(f"\n[yellow]Operation: {op_type.title()}[/yellow] ({len(op_changes)} files)")
        for change in op_changes:
            console.print(f"\n[cyan]File:[/cyan] {change.path}")
            if change.description:
                console.print(f"  [dim]Description:[/dim] {change.description}")
                
            if op_type == 'rename_file':
                console.print(f"  [dim]New Path:[/dim] {change.new_path}")
                
            elif op_type == 'modify_file':
                console.print("  [dim]Modifications:[/dim]")
                for i, mod in enumerate(change.modifications, 1):
                    console.print(f"    [white]#{i}:[/white]")
                    console.print(f"      Search Length: {len(mod.search_content)} chars")
                    if mod.replace_content is not None:
                        console.print(f"      Replace Length: {len(mod.replace_content)} chars")
                    else:
                        console.print("      Action: Delete")
                        
            elif op_type in ['create_file', 'replace_file']:
                size = len(change.content.encode('utf-8'))
                console.print(f"  [dim]Content Size:[/dim] {size/1024:.1f} KB")

    console.print("\n[blue]End Debug Analysis[/blue]\n")

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
