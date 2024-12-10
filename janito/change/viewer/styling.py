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
    """Format content with highlighting using consistent colors and line numbers"""
    text = Text()
    
    # Find similar lines
    similar_pairs = find_similar_lines(search_lines, replace_lines)
    similar_added_indices = {j for _, j, _ in similar_pairs}
    similar_deleted_indices = {i for i, _, _ in similar_pairs}

    # Create sets of lines for comparison
    search_set = set(search_lines)
    replace_set = set(replace_lines)
    common_lines = search_set & replace_set


    def add_line(line: str, prefix: str = " ", line_type: str = 'unchanged'):
        valid_types = {'unchanged', 'deleted', 'added'}
        if line_type not in valid_types:
            line_type = 'unchanged'
            
        bg_color = current_theme.line_backgrounds.get(line_type, current_theme.line_backgrounds['unchanged'])
        style = f"{current_theme.text_color} on {bg_color}"
        
        # Apply background color to prefix and surrounding spaces
        text.append(f"{prefix} ", style=style)
        text.append(line, style=style)
        text.append(" " * 1000 + "\n", style=style)

    for i, line in enumerate(lines):
        if line in common_lines:
            add_line(line, " ", 'unchanged')
        elif not is_search:
            add_line(line, "✚", 'added')
        else:
            if i in similar_deleted_indices:
                for del_idx, add_idx, _ in similar_pairs:
                    if del_idx == i:
                        add_line(line, "✕", 'deleted')
                        break
            else:
                add_line(line, "✕", 'deleted')
    
    return text

def create_legend_items() -> Text:
    """Create unified legend status bar"""
    legend = Text()
    legend.append(" Unchanged ", style=f"{current_theme.text_color} on {current_theme.line_backgrounds['unchanged']}")
    legend.append(" │ ", style="dim")
    legend.append(" ✕ Deleted ", style=f"{current_theme.text_color} on {current_theme.line_backgrounds['deleted']}")
    legend.append(" │ ", style="dim")
    legend.append(" ✚ Added ", style=f"{current_theme.text_color} on {current_theme.line_backgrounds['added']}")
    return legend
