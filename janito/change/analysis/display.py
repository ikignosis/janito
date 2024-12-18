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

    # Option header with fixed width for consistent centering
    header_text = f"Option {option.letter}"
    header = Text()
    header.append(" " * ((20 - len(header_text)) // 2))
    header.append(header_text, style="bold cyan")
    content.append(header)
    content.append("\n")

    # Centered separator
    separator = Text()
    separator.append("═" * 20, style="cyan")
    content.append(separator)
    content.append("\n")

    # Summary with proper centering
    summary_lines = option.summary.split()
    current_line = []
    line_length = 0

    # Word wrap summary to fit width
    for word in summary_lines:
        if line_length + len(word) + 1 <= 20:
            current_line.append(word)
            line_length += len(word) + 1
        else:
            if current_line:
                line_text = " ".join(current_line)
                padding = (20 - len(line_text)) // 2
                content.append(" " * padding + line_text + "\n")
            current_line = [word]
            line_length = len(word)

    if current_line:
        line_text = " ".join(current_line)
        padding = (20 - len(line_text)) // 2
        content.append(" " * padding + line_text)
    content.append("\n\n")

    # Description section with fixed-width centering
    if option.description_items:
        desc_text = "Description"
        padding = (20 - len(desc_text)) // 2
        desc_header = Text()
        desc_header.append(" " * padding + desc_text, style="bold cyan")
        content.append(desc_header)
        content.append("\n")
        desc_separator = Text("─" * 20, style="cyan")
        content.append(desc_separator)
        content.append("\n")
        for item in option.description_items:
            content.append(f"• {item}\n")
        content.append("\n")

    # Affected files section with fixed-width centering
    if option.affected_files:
        files_text = "Affected Files"
        padding = (20 - len(files_text)) // 2
        files_header = Text()
        files_header.append(" " * padding + files_text, style="bold cyan")
        content.append(files_header)
        content.append("\n")
        files_separator = Text("─" * 20, style="cyan")
        content.append(files_separator)
        content.append("\n")

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
                        # Center the arrow in the space
                        padding = len(current_dir)
                        left_pad = (padding - 1) // 2  # -1 for arrow width
                        right_pad = padding - left_pad - 1
                        dir_display = " " * left_pad + "↑" + " " * right_pad
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