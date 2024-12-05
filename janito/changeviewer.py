from pathlib import Path
from rich.console import Console
from rich.text import Text
from typing import TypedDict
import difflib

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
    """Display file changes using unified diff format"""
    # Show header
    console.print(f"\n[bold blue]Changes for {filepath}[/bold blue]")
    console.print(f"[dim]{description}[/dim]\n")
    
    # Generate diff with file-specific labels
    filename = filepath.name
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f'{filename}_old',
        tofile=f'{filename}_new',
        lineterm=''
    )
    
    # Print diff with colors
    for line in diff:
        if line.startswith('+++'):
            console.print(Text(line.rstrip(), style="bold green"))
        elif line.startswith('---'):
            console.print(Text(line.rstrip(), style="bold red"))
        elif line.startswith('+'):
            console.print(Text(line.rstrip(), style="green"))
        elif line.startswith('-'):
            console.print(Text(line.rstrip(), style="red"))
        elif line.startswith('@@'):
            console.print(Text(line.rstrip(), style="cyan"))
        else:
            console.print(Text(line.rstrip()))