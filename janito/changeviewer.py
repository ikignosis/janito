from pathlib import Path
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from typing import TypedDict
import difflib
from rich import box

class FileChange(TypedDict):
    """Type definition for a file change"""
    description: str
    new_content: str

def show_file_changes(console: Console, filepath: Path, original: str, new_content: str, description: str) -> None:
    """Display side by side comparison of file changes"""
    half_width = (console.width - 3) // 2
    
    # Show header
    console.print(f"\n[bold blue]Changes for {filepath}[/bold blue]")
    console.print(f"[dim]{description}[/dim]\n")
    
    # Show side by side content
    console.print(Text("OLD".center(half_width) + "│" + "NEW".center(half_width), style="blue bold"))
    console.print(Text("─" * half_width + "┼" + "─" * half_width, style="blue"))
    
    old_lines = original.splitlines()
    new_lines = new_content.splitlines()
    
    for i in range(max(len(old_lines), len(new_lines))):
        old = old_lines[i] if i < len(old_lines) else ""
        new = new_lines[i] if i < len(new_lines) else ""
        
        old_text = Text(f"{old:<{half_width}}", style="red" if old != new else None)
        new_text = Text(f"{new:<{half_width}}", style="green" if old != new else None)
        console.print(old_text + Text("│", style="blue") + new_text)

def show_diff_changes(console: Console, filepath: Path, original: str, new_content: str, description: str) -> None:
    """Display file changes using unified diff format in a rich panel structure with line numbers"""
    # Create file info table
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_row("File:", Text(str(filepath), style="cyan"))
    info_table.add_row("Type:", Text(filepath.suffix[1:] if filepath.suffix else "unknown", style="yellow"))
    info_table.add_row("Description:", Text(description, style="italic"))

    # Create file info panel
    info_panel = Panel(
        info_table,
        title="File Information",
        title_align="left",
        border_style="blue",
        box=box.ROUNDED
    )

    # Generate diff with line numbers
    old_lines = original.splitlines()
    new_lines = new_content.splitlines()
    diff_lines = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f'{filepath.name}_old',
        tofile=f'{filepath.name}_new',
        lineterm=''
    ))

    # Format diff content with colors and line numbers
    diff_content = Text()
    line_num_old = 1
    line_num_new = 1
    
    for line in diff_lines:
        # Skip the header lines
        if line.startswith('---') or line.startswith('+++'):
            diff_content.append(f"{line}\n", style="bold red" if line.startswith('---') else "bold green")
            continue
            
        # Handle chunk headers
        if line.startswith('@@'):
            diff_content.append(f"{line}\n", style="cyan")
            # Parse line numbers from chunk header
            numbers = line[line.find('-'):line.find(' @@')].replace(' ', '').split(',')
            if len(numbers) >= 2:
                line_num_old = int(numbers[0].replace('-', ''))
                line_num_new = int(numbers[1].replace('+', ''))
            continue

        # Add line numbers and content
        if line.startswith('-'):
            diff_content.append(f"{line_num_old:4d} {line}\n", style="red")
            line_num_old += 1
        elif line.startswith('+'):
            diff_content.append(f"{line_num_new:4d} {line}\n", style="green")
            line_num_new += 1
        else:
            diff_content.append(f"{line_num_old:4d} {line}\n")
            line_num_old += 1
            line_num_new += 1

    # Create diff content panel
    diff_panel = Panel(
        diff_content,
        title="Changes",
        title_align="left",
        border_style="blue",
        box=box.ROUNDED
    )

    # Print panels with spacing
    console.print("\n")
    console.print(info_panel)
    console.print()  # Add spacing between panels
    console.print(diff_panel)
    console.print()  # Add spacing after panels