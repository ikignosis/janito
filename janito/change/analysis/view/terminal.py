"""Terminal UI components for analysis display."""

from typing import Dict, List, Optional
from rich.console import Console
from rich.columns import Columns
from rich.text import Text
from rich.panel import Panel
from rich.rule import Rule
from rich.padding import Padding
from rich.prompt import Prompt
from rich import box
from pathlib import Path

from ..options import AnalysisOption
from ..formatting import (
    COLUMN_SPACING,
    MIN_PANEL_WIDTH,
    SECTION_PADDING,
    create_header,
    create_section_header,
    format_file_path
)

def prompt_user(message: str, choices: List[str] = None) -> str:
    """Display a prominent user prompt with optional choices"""
    console = Console()
    term_width = console.width or 80
    console.print()
    console.print(Rule(" User Input Required ", style="bold cyan", align="center"))

    if choices:
        choice_text = f"[cyan]Options: {', '.join(choices)}[/cyan]"
        console.print(Panel(choice_text, box=box.ROUNDED, justify="center"))

    padding = (term_width - len(message)) // 2
    padded_message = " " * padding + message
    return Prompt.ask(f"[bold cyan]{padded_message}[/bold cyan]")

def get_option_selection() -> str:
    """Get user input for option selection with modify option"""
    console = Console()
    term_width = console.width or 80
    message = "Enter option letter or 'M' to modify request"
    padding = (term_width - len(message)) // 2
    padded_message = " " * padding + message

    console.print(f"\n[cyan]{padded_message}[/cyan]")
    while True:
        letter = prompt_user("Select option").strip().upper()
        if letter == 'M' or (letter.isalpha() and len(letter) == 1):
            return letter

        error_msg = "Please enter a valid letter or 'M'"
        error_padding = (term_width - len(error_msg)) // 2
        padded_error = " " * error_padding + error_msg
        console.print(f"[red]{padded_error}[/red]")

def _create_option_content(option: AnalysisOption) -> Text:
    """Create rich formatted content for a single option."""
    content = Text()
    content.append("\n")

    header = create_header(f"Option {option.letter} - {option.summary}")
    content.append(header)
    content.append("\n\n")

    if option.description_items:
        for item in option.description_items:
            content.append("• ", style="cyan")
            content.append(f"{item}\n")
        content.append("\n")

    if option.affected_files:
        files = {status: [] for status in ['New', 'Modified', 'Removed']}
        for file in option.affected_files:
            if '(new)' in file.lower():
                files['New'].append(file)
            elif '(removed)' in file.lower():
                files['Removed'].append(file)
            else:
                files['Modified'].append(file)

        for status, status_files in files.items():
            if status_files:
                content.append(create_section_header(f"{status} Files"))
                content.append("\n")
                for file in sorted(status_files):
                    path = option.get_clean_path(file)
                    is_new_dir = option.is_new_directory(path)
                    content.append(format_file_path(path, status, is_new_dir))
                    content.append("\n")
                content.append("\n")

        content.append("\n")

    return content

def create_columns_layout(options_content: List[Text], term_width: int) -> Columns:
    """Create a columns layout with consistent spacing."""
    num_columns = len(options_content)
    spacing = COLUMN_SPACING * (num_columns - 1)
    safety_margin = 4 + 2

    usable_width = term_width - spacing - safety_margin
    column_width = max((usable_width // num_columns), MIN_PANEL_WIDTH)

    rendered_columns = [
        Padding(content, (0, COLUMN_SPACING // 2))
        for content in options_content
    ]

    return Columns(
        rendered_columns,
        equal=True,
        expand=True,
        width=column_width,
        align="left",
        padding=(0, 0),
    )

def format_analysis(analysis: str, raw: bool = False) -> None:
    """Format and display the analysis output."""
    from ..options import parse_analysis_options

    console = Console()
    term_width = console.width or 100

    if raw:
        console.print(analysis)
        return

    options = parse_analysis_options(analysis)
    if not options:
        console.print("\n[yellow]Warning: No valid options found in response.[/yellow]\n")
        console.print(analysis)
        return

    columns_content = [_create_option_content(options[letter])
                      for letter in sorted(options.keys())]

    columns = create_columns_layout(columns_content, term_width)

    console.print("\n")
    console.print(Text("Analysis Options", style="bold cyan"))
    console.print(Text("─" * term_width, style="cyan dim"))
    console.print(columns)
    console.print(Text("─" * term_width, style="cyan dim"))
    console.print("\n")