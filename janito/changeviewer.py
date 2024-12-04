from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.columns import Columns
from rich.rule import Rule
from rich import box
from rich.text import Text
from pathlib import Path
from typing import Dict, Any, List
import json
from janito.config import config

def format_parsed_changes(changes: List[Dict[str, Any]]) -> None:
    """Format and display parsed changes in a readable way"""
    console = Console()
    
    if config.debug:
        console.print(Rule(" Debug Information ", style="bold red"))
        console.print(json.dumps(changes, indent=2))
        console.print()
        
    # Print summary header
    console.print(Rule(" Changes Summary ", style="bold blue"))
    for change in changes:
        filename = change["filename"]
        if "content" in change:  # File creation
            console.print(f"[green]• Create new file:[/green] {filename}")
        else:  # File modification
            operations = [c["type"] for c in change.get("changes", [])]
            console.print(f"[yellow]• Modify file:[/yellow] {filename}")
            for op in operations:
                console.print(f"  - {op}")
    
    # Display detailed changes
    for change in changes:
        filename = change["filename"]
        filepath = Path(filename)
        console.print()
        console.print(Rule(f" File: {filename} ", style="bold blue"))
        
        if "content" in change:  # File creation
            show_file_creation(change["content"], filepath)
        else:  # File modification
            if filepath.exists():
                file_content = filepath.read_text()
                lines = file_content.splitlines()
            else:
                lines = []
            for c in change.get("changes", []):
                show_change_operation(c, lines)

def show_file_creation(content: str, filepath: Path) -> None:
    """Display new file creation panel with syntax highlighting"""
    console = Console()
    
    # Use actual file extension for syntax highlighting
    file_ext = filepath.suffix.lstrip('.')
    syntax = None
    
    # Use syntax highlighting if we can detect the language
    if len(content.strip()) > 0:
        try:
            syntax = Syntax(
                content.rstrip('\n'), 
                file_ext if file_ext else "text",
                theme="monokai",
                line_numbers=True
            )
        except:
            syntax = Text(content.rstrip('\n'))
    
    header = Text(f"✨ Creating new file: {filepath.name}", style="green")
    
    panel = Panel(
        Columns([
            syntax or Text("Empty file")
        ], padding=1),
        title=header,
        border_style="green",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(panel)

def show_change_operation(change: Dict[str, Any], file_lines: List[str]) -> None:
    """Display a single change operation"""
    console = Console()
    operation = change["type"]
    original_lines = change["original"].splitlines()
    
    # Find line number of original content
    found_at_line = 1
    for i, line in enumerate(file_lines, 1):
        if ''.join(file_lines[i-1:i-1+len(original_lines)]) == change["original"]:
            found_at_line = i
            break

    if operation == "add_after_content":
        show_add_after_change(change, found_at_line, len(original_lines))
    else:
        show_standard_change(change, operation, found_at_line, len(original_lines))

def show_add_after_change(change: Dict[str, Any], line_num: int, num_lines: int) -> None:
    """Display add_after_content change type in a single merged panel"""
    console = Console()
    text = Text.assemble(
        Text(change["original"].rstrip('\n')),
        "\n",
        "─" * 40, " new content ", "─" * 40,
        "\n",
        Text(change["text"].rstrip('\n'))
    )

    
    panel = Panel(
        text,
        title=Text.assemble(("add_after_content", "yellow")),
        border_style="green", 
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(panel)


def show_standard_change(change: Dict[str, Any], operation: str, line_num: int, num_lines: int) -> None:
    """Display standard change types (add_before, replace, delete)"""
    console = Console()
    
    if operation == "add_before_content":
        text = Text.assemble(
            (f"Will be inserted at line {line_num}:", "dim"),
            "\n",
            Text(change["text"].rstrip('\n'))
        )
        panel = Panel(
            text,
            title=Text.assemble((operation, "yellow")),
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        console.print(panel)
    else:
        original_text = Text.assemble(
            Text(change["original"].rstrip('\n'))
        )
        
        original = Panel(
            original_text,
            title=Text.assemble((operation, "yellow"), " - Original"),
            border_style="red",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        
        new = Panel(
            Text(change["text"].rstrip('\n')),
            title="After Change",
            border_style="green", 
            box=box.ROUNDED,
            padding=(1, 2)
        )
        
        console.print(Columns([original, new], padding=(0, 2), expand=False, align="left"))

