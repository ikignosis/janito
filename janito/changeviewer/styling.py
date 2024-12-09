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

    def highlight_changes(old_line: str, new_line: str) -> Text:
        """Highlight the different parts between similar lines"""
        matcher = SequenceMatcher(None, old_line, new_line)
        result = Text()
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                result.append(new_line[j1:j2], style=f"{current_theme.text_color} on {current_theme.line_backgrounds['modified']}")
            else:
                result.append(new_line[j1:j2], style=f"{current_theme.text_color} on {current_theme.line_backgrounds['highlight']}")
        return result

    def add_line(line: str, prefix: str = " ", line_type: str = 'unchanged', old_line: str = None):
        valid_types = {'unchanged', 'deleted', 'modified', 'added'}
        if line_type not in valid_types:
            line_type = 'unchanged'
            
        bg_color = current_theme.line_backgrounds.get(line_type, current_theme.line_backgrounds['unchanged'])
        style = f"{current_theme.text_color} on {bg_color}"
        
        text.append(prefix, style=style)
        text.append(" ")
        
        if old_line is not None and line_type == 'modified':
            text.append(highlight_changes(old_line, line))
        else:
            text.append(line, style=style)
            
        text.append(" " * 1000 + "\n", style=style)

    for i, line in enumerate(lines):
        if line in common_lines:
            add_line(line, " ", 'unchanged')
        elif not is_search:
            if i - len(search_lines) in similar_added_indices:
                # Find corresponding deleted line
                for del_idx, add_idx, _ in similar_pairs:
                    if add_idx == i - len(search_lines):
                        add_line(line, "✚", 'modified', search_lines[del_idx])
                        break
            else:
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
