"""Analysis display module for Janito.

This module handles the formatting and display of analysis results with support
for different display modes and consistent formatting across the application.
"""

from typing import Optional, Dict
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.columns import Columns
from janito.claude import ClaudeAPIAgent
from janito.prompts import parse_options

# Constants for display modes
COMPACT_WIDTH_THRESHOLD = 80  # Switch to compact mode below this width
MIN_PANEL_WIDTH = 80  # Increased from 40 to 80
MIN_COLUMN_WIDTH = 100  # Increased from 50 to 100

def format_analysis(analysis: str, raw: bool = False, claude: Optional[ClaudeAPIAgent] = None) -> None:
    """Format and display the analysis output with enhanced capabilities.
    
    Args:
        analysis: The analysis text to format and display
        raw: Whether to show raw message history
        claude: Optional Claude API agent for message history
    """
    console = Console()
    
    if raw and claude:
        _display_raw_history(claude)
    else:
        options = parse_options(analysis)
        if options:
            _display_options(options)
        else:
            _display_markdown(analysis)

def _display_raw_history(claude: ClaudeAPIAgent) -> None:
    """Display raw message history from Claude agent."""
    console = Console()
    console.print("\n=== Message History ===")
    for role, content in claude.messages_history:
        console.print(f"\n[bold cyan]{role.upper()}:[/bold cyan]")
        console.print(content)
    console.print("\n=== End Message History ===\n")

def _display_options(options: Dict[str, str]) -> None:
    """Display available options in a multi-column layout.
    
    Args:
        options: Dictionary of option letters to option content
    """
    console = Console()
    console.print("\n[bold cyan]Available Options:[/bold cyan]")
    
    # Calculate optimal column width and count based on terminal width
    terminal_width = console.width
    max_columns = max(1, terminal_width // MIN_COLUMN_WIDTH)
    column_width = max(MIN_COLUMN_WIDTH, terminal_width // max_columns - 4)  # -4 for padding
    
    # Create panels for each option
    panels = []
    for letter, content in options.items():
        # Split content into summary and details
        lines = content.split('\n', 1)
        details = lines[1] if len(lines) > 1 else ""
        
        # Create panel content with just the details
        panel_content = Text(details, style="dim white")
        
        panel = Panel(
            panel_content,
            width=column_width,
            box=box.ROUNDED,
            border_style="cyan",
            title=f"Option {letter}",
            title_align="left"
        )
        panels.append(panel)
    
    # Display panels in columns
    columns = Columns(
        panels,
        width=column_width,
        align="left",
        padding=(0, 2),
        expand=True
    )
    console.print(columns)
    console.print()  # Add spacing after options

def _display_markdown(content: str) -> None:
    """Display content in markdown format."""
    console = Console()
    md = Markdown(content)
    console.print(md)