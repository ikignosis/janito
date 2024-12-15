from rich.text import Text
from rich.console import Console
from typing import List
from difflib import SequenceMatcher
from .diff import find_similar_lines, get_line_similarity
from .themes import DEFAULT_THEME, ColorTheme, ThemeType, get_theme_by_type

current_theme = DEFAULT_THEME

def set_theme(theme: ColorTheme) -> None:
    """Set the current color theme"""
    global current_theme
    current_theme = theme

def format_content(lines: List[str], search_lines: List[str], replace_lines: List[str], is_search: bool, operation: str = 'modify') -> Text:
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

        # Add prefix with consistent spacing
        text.append(f"{prefix} ", style=style)

        # Add line content
        text.append(line, style=style)

        # Add padding to ensure full width background
        padding = " " * max(0, 80 - len(line) - 2)  # -2 for prefix and space
        text.append(f"{padding}\n", style=style)

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

def create_legend_items() -> Text:
    """Create unified legend with consistent styling"""
    legend = Text()
    legend.append(" Unchanged ", style=f"{current_theme.text_color} on {current_theme.line_backgrounds['unchanged']}")
    legend.append(" │ ", style="dim")
    legend.append(" ✕ Deleted ", style=f"{current_theme.text_color} on {current_theme.line_backgrounds['deleted']}")
    legend.append(" │ ", style="dim")
    legend.append(" ✚ Added ", style=f"{current_theme.text_color} on {current_theme.line_backgrounds['added']}")
    return legend