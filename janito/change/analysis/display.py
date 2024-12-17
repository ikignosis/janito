"""Display formatting for analysis results."""

from typing import Dict, List
from pathlib import Path
from rich.console import Console, Group
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.padding import Padding
from rich import box
from janito.change.analysis import AnalysisOption
from .options import parse_analysis_options

# Constants for layout configuration
COLUMN_SPACING = 4  # Spacing between columns in characters
MIN_PANEL_WIDTH = 40  # Minimum width for each panel in characters

def _create_option_content(option: AnalysisOption) -> Text:
    """Create formatted content for a single option."""
    content = Text()

    # Option header
    content.append(f"Option {option.letter}\n", style="bold cyan")
    content.append("═" * 20 + "\n", style="cyan")
    content.append(f"{option.summary}\n\n")

    # Description section
    if option.description_items:
        content.append("Description\n", style="bold cyan")
        content.append("─" * 20 + "\n", style="cyan")
        for item in option.description_items:
            content.append(f"• {item}\n")
        content.append("\n")

    # Affected files section
    if option.affected_files:
        content.append("Affected Files\n", style="bold cyan")
        content.append("─" * 20 + "\n", style="cyan")

        # Group files by status
        files = {status: [] for status in ['Modified', 'New', 'Removed']}
        for file in option.affected_files:
            if '(new)' in file.lower():
                files['New'].append(file)
            elif '(removed)' in file.lower():
                files['Removed'].append(file)
            else:
                files['Modified'].append(file)

        # Display with status colors
        styles = {'Modified': 'yellow', 'New': 'green', 'Removed': 'red'}
        prev_dir = None
        for status, status_files in files.items():
            if status_files:
                content.append(f"\n{status}:\n", style=styles[status])
                for file in sorted(status_files):
                    path = option.get_clean_path(file)
                    new_dir = option.is_new_directory(path)
                    dir_marker = " [📁+]" if new_dir else ""
                    style = "bold magenta" if new_dir else styles[status]

                    # Handle directory alignment
                    current_dir = str(Path(path).parent)
                    if prev_dir and current_dir == prev_dir:
                        dir_display = "↑".ljust(len(current_dir))
                    else:
                        dir_display = current_dir
                        prev_dir = current_dir

                    file_name = Path(path).name
                    content.append(f"• {dir_display}/{file_name}{dir_marker}\n", style=style)
                    
    return content

def create_columns_layout(options_content: List[Text], term_width: int) -> Columns:
    """Create a columns layout with consistent spacing."""
    # Calculate optimal column width
    num_columns = len(options_content)
    spacing = COLUMN_SPACING * (num_columns - 1)
    safety_margin = 4

    usable_width = term_width - spacing - safety_margin
    column_width = max((usable_width // num_columns), MIN_PANEL_WIDTH)

    # Create padded columns
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

    # Create content for each option
    columns_content = [_create_option_content(options[letter])
                      for letter in sorted(options.keys())]

    # Create columns layout
    columns = create_columns_layout(columns_content, term_width)

    # Display with minimal decoration
    console.print("\n")
    console.print(Text("Analysis Options", style="bold cyan"))
    console.print(Text("─" * term_width, style="cyan dim"))
    console.print(columns)
    console.print(Text("─" * term_width, style="cyan dim"))
    console.print("\n")