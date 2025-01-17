"""Terminal UI display components for analysis."""

from typing import Dict, List, Text
from rich.console import Console
from rich.columns import Columns
from rich.text import Text
from rich.panel import Panel
from rich.padding import Padding
from rich.style import Style
from pathlib import Path
import os

from ..options import AnalysisOption

# Display configuration constants
MIN_PANEL_WIDTH = 50
COLUMN_SPACING = 4

# Consolidated color and style definitions
COLORS = {
    'new': 'green',
    'modified': 'yellow',
    'removed': 'red',
    'directory': 'blue',
    'separator': 'dim',
    'repeat': 'dim cyan',
    'header': 'bold cyan',
    'rule': 'cyan dim',
    'option_letter': 'bold yellow',
    'option_summary': 'white'
}

# File status indicators
STATUS_EMOJI = {
    'new': '✨ ',
    'modified': '🔄 ',
    'removed': '🗑️ '
}


def _create_option_content(option: AnalysisOption) -> Text:
    """Create rich formatted content for a single option."""
    content = Text()
    content.append("\n")

    # Header
    header_text = f"Option {option.letter}: {option.summary}"
    padding_str = " " * ((MIN_PANEL_WIDTH - len(header_text)) // 2)
    
    content.append(padding_str)
    content.append("Option ", style=COLORS['header'])
    content.append(option.letter, style=COLORS['option_letter'])
    content.append(": ", style=COLORS['header'])
    content.append(option.summary, style=COLORS['option_summary'])
    content.append("\n")
    content.append(padding_str + "=" * len(header_text), style=COLORS['rule'])
    content.append("\n\n")

    # Action plan
    if option.action_plan:
        for item in option.action_plan:
            content.append("• ", style="cyan")
            content.append(f"{item}\n")
        content.append("\n")

    # File changes
    if option.modified_files:
        files = {'New': [], 'Modified': [], 'Removed': []}
        for file in option.modified_files:
            if '(new)' in file.lower():
                files['New'].append(file)
            elif '(removed)' in file.lower():
                files['Removed'].append(file)
            else:
                files['Modified'].append(file)

        for status, status_files in files.items():
            if not status_files:
                continue

            content.append(f"{status} Files\n", style=COLORS['header'])
            content.append("─" * MIN_PANEL_WIDTH + "\n", style=COLORS['rule'])

            seen_dirs = set()
            for file in sorted(status_files):
                path = Path(option.get_clean_path(file))
                status_emoji = STATUS_EMOJI[status.lower()]
                # Add status emoji at the start of the line
                content.append(status_emoji, style=COLORS[status.lower()])
                if path.parent != Path('.'):
                    if str(path.parent) in seen_dirs:
                        content.append("↑".center(len(str(path.parent))), style=COLORS['repeat'])
                    else:
                        content.append(str(path.parent), style=COLORS['directory'])
                        seen_dirs.add(str(path.parent))
                    content.append(os.path.sep, style=COLORS['separator'])
                content.append(f"{path.name}\n", style=COLORS[status.lower()])
            content.append("\n")

    return content

def create_columns_layout(options_content: List[Text], term_width: int) -> Columns:
    """Create a columns layout with consistent spacing."""
    num_columns = len(options_content)
    usable_width = term_width - (COLUMN_SPACING * (num_columns - 1)) - 6
    column_width = max((usable_width // num_columns), MIN_PANEL_WIDTH + COLUMN_SPACING)

    rendered_items = [
        Padding(content, (0, COLUMN_SPACING // 2))
        for content in options_content
    ]

    return Columns(
        rendered_items,
        equal=True,
        expand=True,
        width=column_width,
        align="center",
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

    columns_content = [
        _create_option_content(options[letter])
        for letter in sorted(options.keys())
    ]

    columns = create_columns_layout(columns_content, term_width)

    console.print("\n")
    console.print(Text("Available Options", style=COLORS['header']), justify="center")
    console.print(Text("─" * term_width, style=COLORS['rule']))
    console.print(columns)
    console.print("\n")
