from pathlib import Path
from typing import List, Tuple, Optional
import tempfile
import shutil
import subprocess
from rich.console import Console
from rich.text import Text
from rich.prompt import Confirm
from rich.panel import Panel
from rich import box
from rich.columns import Columns
from datetime import datetime

from janito.fileparser import FileChange, validate_python_syntax
from janito.changeviewer import preview_all_changes
from janito.config import config
from janito.changehistory import get_history_file_path
from .applier import apply_single_change

def run_test_command(preview_dir: Path, test_cmd: str) -> Tuple[bool, str, Optional[str]]:
    """Run test command in preview directory.
    Returns (success, output, error)"""
    try:
        result = subprocess.run(
            test_cmd,
            shell=True,
            cwd=preview_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return (
            result.returncode == 0,
            result.stdout,
            result.stderr if result.returncode != 0 else None
        )
    except subprocess.TimeoutExpired:
        return False, "", "Test command timed out after 5 minutes"
    except Exception as e:
        return False, "", f"Error running test: {str(e)}"

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

def preview_and_apply_changes(changes: List[FileChange], workdir: Path, test_cmd: str = None) -> bool:
    """Preview changes and apply if confirmed"""
    console = Console()
    
    if not changes:
        console.print("\n[yellow]No changes were found to apply[/yellow]")
        return False

    # Show change preview
    preview_all_changes(console, changes)

    with tempfile.TemporaryDirectory() as temp_dir:
        preview_dir = Path(temp_dir)
        console.print("\n[blue]Creating preview in temporary directory...[/blue]")
        
        # Create backup directory
        backup_dir = workdir / '.janito' / 'backups' / datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy existing files to preview directory
        if workdir.exists():
            # Create backup before applying changes
            if config.verbose:
                console.print(f"[blue]Creating backup at:[/blue] {backup_dir}")
            shutil.copytree(workdir, backup_dir, ignore=shutil.ignore_patterns('.janito'))
            # Copy to preview directory, excluding .janito
            shutil.copytree(workdir, preview_dir, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.janito'))
            
            # Create restore script
            restore_script = workdir / '.janito' / 'restore.sh'
            restore_script.parent.mkdir(parents=True, exist_ok=True)
            script_content = f"""#!/bin/bash
# Restore script generated by Janito
# Restores files from backup created at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Exit on error
set -e

# Check if backup directory exists
if [ ! -d "{backup_dir}" ]; then
    echo "Error: Backup directory not found at {backup_dir}"
    exit 1
fi

# Restore files from backup
echo "Restoring files from backup..."
cp -r "{backup_dir}"/* "{workdir}/"

echo "Files restored successfully from {backup_dir}"
"""
            restore_script.write_text(script_content)
            restore_script.chmod(0o755)  # Make script executable
            
            if config.verbose:
                console.print(f"[blue]Created restore script at:[/blue] {restore_script}")
        
    
    # Apply changes to preview directory
        any_errors = False
        for change in changes:
            console.print(f"[dim]Previewing changes for {change.path}...[/dim]")
            success, error = apply_single_change(change.path, change, workdir, preview_dir)
            if not success:
                if "file already exists" in str(error):
                    console.print(f"\n[red]Error: Cannot create {change.path}[/red]")
                    console.print("[red]File already exists and overwriting is not allowed.[/red]")
                else:
                    console.print(f"\n[red]Error previewing changes for {change.path}:[/red]")
                    console.print(f"[red]{error}[/red]")
                any_errors = True
                continue
        
        if any_errors:
            console.print("\n[red]Some changes could not be previewed. Aborting.[/red]")
            return False

        # Validate Python syntax for all modified Python files
        python_files = {change.path for change in changes if change.path.suffix == '.py'}
        for filepath in python_files:
            preview_path = preview_dir / filepath
            is_valid, error_msg = validate_python_syntax(preview_path.read_text(), preview_path)
            if not is_valid:
                console.print(f"\n[red]Python syntax validation failed for {filepath}:[/red]")
                console.print(f"[red]{error_msg}[/red]")
                return False

        # Run tests if specified
        if test_cmd:
            console.print(f"\n[cyan]Testing changes in preview directory:[/cyan] {test_cmd}")
            success, output, error = run_test_command(preview_dir, test_cmd)
            
            if output:
                console.print("\n[bold]Test Output:[/bold]")
                console.print(Panel(output, box=box.ROUNDED))
            
            if not success:
                console.print("\n[red bold]Tests failed in preview. Changes will not be applied.[/red bold]")
                if error:
                    console.print(Panel(error, title="Error", border_style="red"))
                return False

        # Final confirmation to apply to working directory
        if not Confirm.ask("\n[cyan bold]Apply previewed changes to working directory?[/cyan bold]"):
            console.print("\n[yellow]Changes were only previewed, not applied to working directory[/yellow]")
            console.print("[green]Changes are stored in the history directory and can be applied later using:[/green]")
            changes_file = get_history_file_path(workdir)
            console.print(f"[cyan]  {changes_file.relative_to(workdir)}[/cyan]")
            return False

        # Copy changes to actual files
        console.print("\n[blue]Applying changes to working directory...[/blue]")
        for change in changes:
            console.print(f"[dim]Applying changes to {change.path}...[/dim]")
            target_path = workdir / change.path
            
            if change.remove_file:
                if target_path.exists():
                    target_path.unlink()
                    console.print(f"[red]Removed {change.path}[/red]")
            else:
                preview_path = preview_dir / change.path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(preview_path, target_path)

        console.print("\n[green]Changes successfully applied to working directory![/green]")
        return True