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

MIN_PANEL_WIDTH = 40   # Minimum width for each panel

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
    affected_files: List[str]  # Now preserves (new) markers
    description_items: List[str]

    def get_clean_path(self, file_path: str) -> str:
        """Get clean path without (new) marker"""
        return file_path.split(' (')[0].strip()
        
    def is_new_file(self, file_path: str) -> bool:
        """Check if file is marked as new"""
        return '(new)' in file_path

    def get_affected_paths(self, workdir: Optional[Path] = None) -> List[Path]:
        """Get list of affected paths, resolving against workdir if provided"""
        paths = []
        for file_path in self.affected_files:
            clean_path = self.get_clean_path(file_path)
            path = workdir / clean_path if workdir else Path(clean_path)
            paths.append(path)
        return paths

CHANGE_ANALYSIS_PROMPT = """
Current files:
<files>
{files_content}
</files>

Considering the above current files content, provide options for the requested change in the following format:

A. Keyword summary of the change
-----------------
Description:
- Concise description of the change

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
    """Display available options with left-aligned content and horizontally centered panels."""
    console = Console()
    
    # Display centered title using Rule
    console.print()
    console.print(Rule(" Available Options ", style="bold cyan", align="center"))
    console.print()
    
    # Calculate optimal width based on terminal
    term_width = console.width or 100
    panel_width = max(MIN_PANEL_WIDTH, (term_width // 2) - 10)  # Width for two columns
    
    # Create panels for each option
    panels = []
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
                # Use yellow for existing files, green for new files
                color = "green" if '(new)' in file else "yellow"
                content.append(f"• {file}\n", style=color)

        # Create panel with consistent styling
        panel = Panel(
            content,
            box=box.ROUNDED,
            border_style="cyan",
            title=f"Option {letter}: {option.summary}",
            title_align="center",
            padding=(1, 2),
            width=panel_width
        )
        panels.append(panel)
    
    # Display panels in columns with center alignment
    if panels:
        # Group panels into pairs for two columns
        for i in range(0, len(panels), 2):
            pair = panels[i:i+2]
            columns = Columns(
                pair,
                align="center",
                expand=True,
                equal=True,
                padding=(0, 2)
            )
            console.print(columns)
            console.print()  # Add spacing between rows

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


def format_analysis(analysis: str, raw: bool = False, claude: Optional[ClaudeAPIAgent] = None, workdir: Optional[Path] = None) -> None:
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
    """Parse options from the response text using a line-based approach."""
    options = {}
    
    # Extract content up to END_OF_OPTIONS
    if 'END_OF_OPTIONS' in response:
        response = response.split('END_OF_OPTIONS')[0]
    
    lines = response.splitlines()
    current_option = None
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for new option starting with letter
        if len(line) >= 2 and line[0].isalpha() and line[1] == '.' and line[0].isupper():
            if current_option:
                options[current_option.letter] = current_option
            
            letter = line[0]
            summary = line[2:].strip()
            current_option = AnalysisOption(
                letter=letter,
                summary=summary,
                affected_files=[],
                description_items=[]
            )
            current_section = None
            continue
            
        # Skip separator lines
        if line.startswith('---'):
            continue
            
        # Check for section headers
        if line.startswith('Description:'):
            current_section = 'description'
            continue
        elif line.startswith('Affected files:'):
            current_section = 'files'
            continue
            
        # Process content based on current section
        if current_option and current_section and line:
            if current_section == 'description':
                # Strip bullet points and whitespace
                item = line.lstrip(' -•').strip()
                if item:
                    current_option.description_items.append(item)
            elif current_section == 'files':
                # Only strip bullet points, preserve (new) marker
                file_path = line.lstrip(' -').strip()
                if file_path:
                    current_option.affected_files.append(file_path)
    
    # Add the last option if exists
    if current_option:
        options[current_option.letter] = current_option
    
    return options

def build_request_analysis_prompt(files_content: str, request: str) -> str:
    """Build prompt for information requests"""
    return CHANGE_ANALYSIS_PROMPT.format(
        files_content=files_content,
        request=request
    )
