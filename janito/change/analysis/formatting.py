"""Centralized formatting utilities for analysis display."""

from typing import Dict, List, Text
from rich.text import Text
from rich.columns import Columns
from rich.padding import Padding
from pathlib import Path

# Layout constants
COLUMN_SPACING = 6  # Increased spacing between columns
MIN_PANEL_WIDTH = 45  # Wider minimum width for better readability
SECTION_PADDING = (2, 0)  # More vertical padding

# Color scheme constants
STATUS_COLORS = {
    'new': 'bright_green',
    'modified': 'yellow',
    'removed': 'red',
    'default': 'white'
}

STRUCTURAL_COLORS = {
    'directory': 'dim',
    'separator': 'blue dim',
    'repeat': 'bright_magenta bold'
}

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

def format_file_path(path: str, status: str, max_dir_length: int = 0, is_repeated: bool = False) -> Text:
    """Format file path with status indicators and consistent alignment.

    Args:
        path: File path to format
        status: File status (Modified, New, Removed)
        max_dir_length: Maximum directory name length for padding
        is_repeated: Whether this directory was seen before
    """
    content = Text()
    style = STATUS_COLORS.get(status.lower(), STATUS_COLORS['default'])

    parts = Path(path).parts
    parent_dir = str(Path(path).parent)

    if parent_dir != '.':
        # Add 4 spaces for consistent base padding
        base_padding = 4
        dir_padding = max_dir_length + base_padding

        if is_repeated:
            # Add arrow with consistent spacing
            content.append(" " * base_padding)
            content.append("↑ ", style="magenta")
            content.append(" " * (dir_padding - base_padding - 2))
        else:
            # Left-align directory name with consistent padding
            content.append(" " * base_padding)
            content.append(parent_dir, style="dim")
            content.append(" " * (dir_padding - len(parent_dir) - base_padding))

    # Add filename with consistent spacing
    content.append(parts[-1], style=style)
    return content