"""Analysis display module for Janito.

This module handles the formatting and display of analysis results, option selection,
and related functionality for the Janito application.
"""

from typing import Optional, Dict, List, Tuple
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.columns import Columns
from rich.rule import Rule
from rich.prompt import Prompt
from janito.claude import ClaudeAPIAgent
from janito.prompts import (
    parse_analysis_options,
    build_request_analisys_prompt,
    build_selected_option_prompt,
    AnalysisOption
)
from janito.scan import collect_files_content
from janito.common import progress_send_message
from janito.config import config

# Constants for display modes
COMPACT_WIDTH_THRESHOLD = 80  # Switch to compact mode below this width
MIN_PANEL_WIDTH = 80  # Increased from 40 to 80
MIN_COLUMN_WIDTH = 100  # Increased from 50 to 100

def prompt_user(message: str, choices: List[str] = None) -> str:
    """Display a prominent user prompt with optional choices"""
    console = Console()
    console.print()
    console.print(Rule(" User Input Required ", style="bold cyan"))
    
    if choices:
        choice_text = f"[cyan]Options: {', '.join(choices)}[/cyan]"
        console.print(Panel(choice_text, box=box.ROUNDED))
    
    return Prompt.ask(f"[bold cyan]> {message}[/bold cyan]")

def validate_option_letter(letter: str, options: dict) -> bool:
    """Validate if the given letter is a valid option or 'M' for modify"""
    return letter.upper() in options or letter.upper() == 'M'

def get_option_selection() -> str:
    """Get user input for option selection with modify option"""
    console = Console()
    console.print("\n[cyan]Enter option letter or 'M' to modify request[/cyan]")
    while True:
        letter = prompt_user("Select option").strip().upper()
        if letter == 'M' or (letter.isalpha() and len(letter) == 1):
            return letter
        console.print("[red]Please enter a valid letter or 'M'[/red]")

def _display_options(options: Dict[str, AnalysisOption]) -> None:
    """Display available options in a multi-column layout.
    
    Args:
        options: Dictionary of option letters to AnalysisOption objects
    """
    console = Console()
    
    # Display centered title using Rule instead of Panel
    console.print()
    console.print(Rule(" Available Options ", style="bold cyan", align="center"))
    console.print()
    
    # Calculate optimal column width and count based on terminal width
    terminal_width = console.width
    max_columns = max(1, terminal_width // MIN_COLUMN_WIDTH)
    column_width = max(MIN_COLUMN_WIDTH, terminal_width // max_columns - 4)  # -4 for padding
    
    # Create panels for each option
    panels = []
    for letter, option in options.items():
        content = Text()
        
        # Display description as paragraph
        content.append("Description:\n", style="bold cyan")
        content.append(f"{option.description}\n\n", style="white")
        
        # Then display affected files
        if option.affected_files:
            content.append("Affected files:\n", style="bold cyan")
            for file in option.affected_files:
                content.append(f"• {file}\n", style="yellow")
        
        panel = Panel(
            content,
            width=column_width,
            box=box.ROUNDED,
            border_style="cyan",
            title=f"Option {letter}: {option.summary}",
            title_align="center"
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

def _display_raw_history(claude: ClaudeAPIAgent) -> None:
    """Display raw message history from Claude agent."""
    console = Console()
    console.print("\n=== Message History ===")
    for role, content in claude.messages_history:
        console.print(f"\n[bold cyan]{role.upper()}:[/bold cyan]")
        console.print(content)
    console.print("\n=== End Message History ===\n")

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
        options = parse_analysis_options(analysis)
        if options:
            _display_options(options)
        else:
            _display_markdown(analysis)

def get_history_path(workdir: Path) -> Path:
    """Create and return the history directory path"""
    history_dir = workdir / '.janito' / 'history'
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir

def get_timestamp() -> str:
    """Get current UTC timestamp in YMD_HMS format with leading zeros"""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

def save_to_file(content: str, prefix: str, workdir: Path) -> Path:
    """Save content to a timestamped file in history directory"""
    history_dir = get_history_path(workdir)
    timestamp = get_timestamp()
    filename = f"{timestamp}_{prefix}.txt"
    file_path = history_dir / filename
    file_path.write_text(content)
    return file_path