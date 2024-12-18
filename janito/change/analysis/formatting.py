"""Centralized formatting utilities for analysis display."""

from typing import Dict, List, Text
from rich.text import Text
from rich.columns import Columns
from rich.padding import Padding
from pathlib import Path

# Layout constants
COLUMN_SPACING = 4
MIN_PANEL_WIDTH = 40
SECTION_PADDING = (1, 0)

def create_header(text: str, style: str = "bold cyan") -> Text:
    """Create formatted header with separator."""
    content = Text()
    content.append(text, style=style)
    content.append("\n")
    content.append("═" * len(text), style="cyan")
    return content

def create_section_header(text: str, width: int = 20) -> Text:
    """Create centered section header with separator."""
    content = Text()
    padding = (width - len(text)) // 2
    content.append(" " * padding + text, style="bold cyan")
    content.append("\n")
    content.append("─" * width, style="cyan")
    return content

def format_file_path(path: str, status: str, is_new_dir: bool) -> Text:
    """Format file path with status indicators."""
    content = Text()
    style = {
        'Modified': 'yellow',
        'New': 'green',
        'Removed': 'red'
    }.get(status, 'default')

    if is_new_dir:
        style = "bold magenta"

    dir_marker = " [📁+]" if is_new_dir else ""
    content.append(f"• {path}{dir_marker}", style=style)
    return content