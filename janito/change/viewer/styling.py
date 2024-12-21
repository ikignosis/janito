from rich.text import Text
from rich.console import Console
from typing import List, Optional
from difflib import SequenceMatcher
from .diff import find_similar_lines, get_line_similarity
from .themes import DEFAULT_THEME, ColorTheme, ThemeType, get_theme_by_type

current_theme = DEFAULT_THEME

def set_theme(theme: ColorTheme) -> None:
    """Set the current color theme"""
    global current_theme
    current_theme = theme

def format_content(lines: List[str], search_lines: List[str], replace_lines: List[str], is_search: bool, width: int = 80, is_delete: bool = False, is_removal: bool = False) -> Text:
    """Format content with unified highlighting and clean indentation

    Args:
        lines: Lines to format
        search_lines: Original content lines for comparison
        replace_lines: New content lines for comparison
        is_search: Whether this is search content (vs replace content)
        width: Target width for padding
        is_delete: Whether this is a deletion operation
    """
    text = Text()

    # For delete or removal operations, show lines with appropriate styling
    if is_delete or is_removal:
        bg_color = current_theme.line_backgrounds['removed' if is_removal else 'deleted']
        style = f"{current_theme.text_color} on {bg_color}"

        for line in lines:
            # Calculate padding to fill width
            content_width = len(line)
            padding = " " * max(0, width - content_width)

            # Add content with consistent background
            text.append(line, style=style)
            text.append(padding, style=style)
            text.append("\n", style=style)
        return text

    # Find similar lines for better diff visualization
    similar_pairs = find_similar_lines(search_lines, replace_lines)
    similar_added = {j for _, j, _ in similar_pairs}
    similar_deleted = {i for i, _, _ in similar_pairs}

    # Create sets for comparison
    search_set = set(search_lines)
    replace_set = set(replace_lines)
    common_lines = search_set & replace_set

    def add_line(line: str, line_type: str = 'unchanged'):
        bg_color = current_theme.line_backgrounds.get(line_type, current_theme.line_backgrounds['unchanged'])
        style = f"{current_theme.text_color} on {bg_color}"

        # Calculate padding to fill the width
        padding = " " * max(0, width - len(line))

        # Add content and padding with consistent background
        text.append(line, style=style)
        text.append(padding, style=style)
        text.append("\n", style=style)

    for i, line in enumerate(lines):
        if not line.strip():  # Handle empty lines
            add_line("", 'unchanged')
        elif line in common_lines:
            add_line(line, 'unchanged')
        elif not is_search:
            add_line(line, 'added')
        else:
            add_line(line, 'deleted')

    return text

from rich.panel import Panel
from rich.columns import Columns

def create_legend_items(console: Console) -> Panel:
    """Create a compact legend panel with color blocks

    Args:
        console: Console instance for width calculation
    """
    text = Text()
    term_width = console.width or 120

    # Add color blocks for each type
    for label, bg_type in [("Unchanged", "unchanged"),
                          ("Deleted", "deleted"),
                          ("Added", "added")]:
        style = f"{current_theme.text_color} on {current_theme.line_backgrounds[bg_type]}"
        text.append("  ", style=style)  # Color block
        text.append(" " + label + " ")  # Label with spacing

    return Panel(
        text,
        padding=(0, 1),
        expand=False,
        title="Legend",
        title_align="center"
    )