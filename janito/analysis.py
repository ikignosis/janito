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
from janito.scan import collect_files_content
from janito.common import progress_send_message
from janito.config import config
from dataclasses import dataclass
import re

def get_history_file_type(filepath: Path) -> str:
    """Determine the type of saved file based on its name"""
    name = filepath.name.lower()
    if 'changes' in name:
        return 'changes'
    elif 'selected' in name:
        return 'selected'
    elif 'analysis' in name:
        return 'analysis'
    elif 'response' in name:
        return 'response'
    return 'unknown'

@dataclass
class AnalysisOption:
    letter: str
    summary: str
    affected_files: List[str]
    description_items: List[str]  # Changed from description to description_items

CHANGE_ANALYSIS_PROMPT = """
Current files:
<files>
{files_content}
</files>

Considering the above current files content, provide options for the requested change in the following format:

A. Keyword summary of the change
-----------------
Description:
- Detailed description of the change

Affected files:
- file1.py
- file2.py (new)
-----------------
END_OF_OPTIONS (mandatory marker)

RULES:
- do NOT provide the content of the files
- do NOT offer to implement the changes

Request:
{request}
"""



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
    """Display available options in a vertical layout.
    
    Args:
        options: Dictionary of option letters to AnalysisOption objects
    """
    console = Console()
    
    # Display centered title using Rule
    console.print()
    console.print(Rule(" Available Options ", style="bold cyan", align="center"))
    console.print()
    
    # Calculate panel width based on terminal width
    terminal_width = console.width
    panel_width = min(terminal_width - 4, MIN_PANEL_WIDTH)
    
    # Create and display panels for each option
    for letter, option in options.items():
        content = Text()
        
        # Display description as bullet points
        content.append("Description:\n", style="bold cyan")
        for item in option.description_items:
            content.append(f"• {item}\n", style="white")
        content.append("\n")
        
        # Display affected files
        if option.affected_files:
            content.append("Affected files:\n", style="bold cyan")
            for file in option.affected_files:
                content.append(f"• {file}\n", style="yellow")
        
        panel = Panel(
            content,
            width=panel_width,
            box=box.ROUNDED,
            border_style="cyan",
            title=f"Option {letter}: {option.summary}",
            title_align="center"
        )
        console.print(panel)
        console.print()  # Add spacing between panels

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
    """Format and display the analysis output with enhanced capabilities."""
    console = Console()
    
    if raw and claude:
        _display_raw_history(claude)
    else:
        options = parse_analysis_options(analysis)
        if options:
            _display_options(options)
        else:
            console.print("\n[yellow]Warning: No valid options found in response. Displaying as markdown.[/yellow]\n")
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



def parse_analysis_options(response: str) -> dict[str, AnalysisOption]:
    """Parse options from the response text using letter-based format until END_OF_OPTIONS"""
    options = {}
    
    # Extract content up to END_OF_OPTIONS
    if 'END_OF_OPTIONS' in response:
        response = response.split('END_OF_OPTIONS')[0]
        
    # Pattern to match sections between dashed lines
    pattern = r'([A-Z])\.\s+([^\n]+?)\s*-+\s*Description:\s*(.*?)\s*Affected files:\s*(.*?)\s*-+\s*(?:[A-Z]\.|$)'
    matches = re.finditer(pattern, response, re.DOTALL)
    
    for match in matches:
        option_letter = match.group(1)
        summary = match.group(2).strip()
        
        # Parse description into bullet points
        description_items = []
        raw_description = (match.group(3) or "").strip()
        for line in raw_description.split('\n'):
            line = line.strip(' -•\n')
            if line:
                description_items.append(line)
        
        files_section = match.group(4) or ""
        
        # Parse affected files, now handling the "- filename (modified)" format
        files = []
        for line in files_section.strip().split('\n'):
            line = line.strip(' -\n')
            if line:
                # Strip any (modified) or (new) annotations
                file_path = re.sub(r'\s*\([^)]+\)\s*$', '', line)
                files.append(file_path)
        
        option = AnalysisOption(
            letter=option_letter,
            summary=summary,
            affected_files=files,
            description_items=description_items
        )
        options[option_letter] = option
        
    return options

def build_request_analysis_prompt(files_content: str, request: str) -> str:
    """Build prompt for information requests"""
    return CHANGE_ANALYSIS_PROMPT.format(
        files_content=files_content,
        request=request
    )