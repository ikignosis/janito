from rich.text import Text
from typing import List, Set

COLORS = {
    'unchanged': '#98C379',  # Brighter green for unchanged lines
    'removed': '#E06C75',    # Clearer red for removed lines
    'added': '#61AFEF',      # Bright blue for added lines
    'new': '#C678DD',        # Purple for completely new lines
    'relocated': '#61AFEF'   # Use same blue for relocated lines
}

def format_content(lines: List[str], search_lines: List[str], replace_lines: List[str], is_search: bool) -> Text:
    """Format content with highlighting using consistent colors and line numbers"""
    text = Text()
    
    # Create sets of lines for comparison
    search_set = set(search_lines)
    replace_set = set(replace_lines)
    common_lines = search_set & replace_set
    new_lines = replace_set - search_set

    def add_line(line: str, style: str, prefix: str = " "):
        # Special handling for icons
        if style == COLORS['relocated']:
            prefix = "⇄"
        elif style == COLORS['removed'] and prefix == "-":
            prefix = "✕"
        elif style == COLORS['new'] or (style == COLORS['added'] and prefix == "+"):
            prefix = "✚"
        text.append(prefix, style=style)
        text.append(f" {line}\n", style=style)

    for line in lines:
        if line in common_lines:
            add_line(line, COLORS['unchanged'], "=")
        elif not is_search and line in new_lines:
            add_line(line, COLORS['new'], "+")
        else:
            style = COLORS['removed'] if is_search else COLORS['added']
            prefix = "✕" if is_search else "+"
            add_line(line, style, prefix)
    
    return text

def create_legend_items() -> List[Text]:
    """Create legend items for the change preview"""
    return [
        Text("Unchanged", style=COLORS['unchanged']),
        Text(" • ", style="dim"),
        Text("Removed", style=COLORS['removed']),
        Text(" • ", style="dim"),
        Text("Relocated", style=COLORS['relocated']),
        Text(" • ", style="dim"),
        Text("New", style=COLORS['new'])
    ]
