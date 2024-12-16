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

def format_content(lines: List[str], search_lines: List[str], replace_lines: List[str], is_search: bool, width: int = 80) -> Text:
    """Format content with unified highlighting and indicators"""
    text = Text()

    # Find similar lines for better diff visualization
    similar_pairs = find_similar_lines(search_lines, replace_lines)
    similar_added = {j for _, j, _ in similar_pairs}
    similar_deleted = {i for i, _, _ in similar_pairs}

    # Create sets for comparison
    search_set = set(search_lines)
    replace_set = set(replace_lines)
    common_lines = search_set & replace_set

    def add_line(line: str, prefix: str = " ", line_type: str = 'unchanged'):
        bg_color = current_theme.line_backgrounds.get(line_type, current_theme.line_backgrounds['unchanged'])
        style = f"{current_theme.text_color} on {bg_color}"

        # Add prefix and content with left alignment
        text.append(f"{prefix} ", style=style)
        text.append(line, style=style)
        text.append("\n", style=style)

    for i, line in enumerate(lines):
        if not line.strip():  # Handle empty lines
            add_line("", " ", 'unchanged')
        elif line in common_lines:
            add_line(line, " ", 'unchanged')
        elif not is_search:
            add_line(line, "✚", 'added')
        else:
            add_line(line, "✕", 'deleted')

    return text

from rich.panel import Panel
from rich.columns import Columns

def create_legend_items(console: Console) -> Panel:
    """Create a compact single panel with all legend items

    Args:
        console: Console instance for width calculation
    """
    text = Text()
    term_width = console.width or 120

    # Add unchanged item
    unchanged_style = f"{current_theme.text_color} on {current_theme.line_backgrounds['unchanged']}"
    text.append(" ", style=unchanged_style)
    text.append(" Unchanged ", style=unchanged_style)

    text.append("  ")  # Spacing between items

    # Add deleted item
    deleted_style = f"{current_theme.text_color} on {current_theme.line_backgrounds['deleted']}"
    text.append("✕", style=deleted_style)
    text.append(" Deleted ", style=deleted_style)

    text.append("  ")  # Spacing between items

    # Add added item
    added_style = f"{current_theme.text_color} on {current_theme.line_backgrounds['added']}"
    text.append("✚", style=added_style)
    text.append(" Added", style=added_style)

    return Panel(
        text,
        padding=(0, 1),
        expand=False
    )