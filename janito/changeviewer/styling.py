from rich.text import Text
from rich.console import Console
from typing import List
from .themes import DEFAULT_THEME, ColorTheme, ThemeType, get_theme_by_type

current_theme = DEFAULT_THEME

def set_theme(theme: ColorTheme) -> None:
    """Set the current color theme"""
    global current_theme
    current_theme = theme

def format_content(lines: List[str], search_lines: List[str], replace_lines: List[str], is_search: bool, operation: str = 'modify') -> Text:
    """Format content with highlighting using consistent colors and line numbers"""
    text = Text()
    
    # Create sets of lines for comparison
    search_set = set(search_lines)
    replace_set = set(replace_lines)
    common_lines = search_set & replace_set
    new_lines = replace_set - search_set

    def add_line(line: str, prefix: str = " ", line_type: str = 'unchanged'):
        # Ensure line_type is one of the valid types
        valid_types = {'unchanged', 'deleted', 'modified', 'added'}
        if line_type not in valid_types:
            line_type = 'unchanged'
            
        bg_color = current_theme.line_backgrounds.get(line_type, current_theme.line_backgrounds['unchanged'])
        style = f"{current_theme.text_color} on {bg_color}"
        
        # Add prefix with background
        text.append(prefix, style=style)
        # Add line content with background and pad with spaces
        text.append(" " + line, style=style)
        # Add newline with same background
        text.append(" " * 1000 + "\n", style=style)

    for line in lines:
        if line in common_lines:
            add_line(line, " ", 'unchanged')
        elif not is_search and line in new_lines:
            add_line(line, "✚", 'added')
        else:
            prefix = "✕" if is_search else "✚"
            line_type = 'deleted' if is_search else 'modified'
            add_line(line, prefix, line_type)
    
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
