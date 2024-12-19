"""User prompts and input handling for analysis."""

from typing import List, Dict
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.prompt import Prompt
from rich import box


from .options import AnalysisOption

# Keep only prompt-related functionality
CHANGE_ANALYSIS_PROMPT = """


Considering the above workset content, provide 3 sections, each identified by a keyword and representing an option.
Each option should include a concise description and a list of affected files.
1st option should be basic style change, 2nd organized style, 3rd exntensible style.
Do not use style as keyword, instead focus on the changes summary.

Use the following format:

A. Keyword summary of the change
-----------------
Description:
- Concise description of the change

Affected files:
- path/file1.py (new)
- path/file2.py (modified)
- path/file3.py (removed)

END_OF_OPTIONS (mandatory marker)

RULES:
- do NOT provide the content of the files
- do NOT offer to implement the changes
- description items should be 80 chars or less

Request:
{request}
"""

def prompt_user(message: str, choices: List[str] = None) -> str:
    """Display a prominent user prompt with optional choices"""
    console = Console()
    term_width = console.width or 80
    console.print()
    console.print(Rule(" User Input Required ", style="bold cyan", align="center"))
    
    if choices:
        choice_text = f"[cyan]Options: {', '.join(choices)}[/cyan]"
        console.print(Panel(choice_text, box=box.ROUNDED, justify="center"))
    
    # Center the prompt with padding
    padding = (term_width - len(message)) // 2
    padded_message = " " * padding + message
    return Prompt.ask(f"[bold cyan]{padded_message}[/bold cyan]")

def validate_option_letter(letter: str, options: Dict[str, AnalysisOption]) -> bool:
    """Validate if the given letter is a valid option or 'M' for modify"""
    if letter.upper() == 'M':
        return True
    return letter.upper() in options

def get_option_selection() -> str:
    """Get user input for option selection with modify option"""
    console = Console()
    term_width = console.width or 80
    message = "Enter option letter or 'M' to modify request"
    padding = (term_width - len(message)) // 2
    padded_message = " " * padding + message
    
    console.print(f"\n[cyan]{padded_message}[/cyan]")
    while True:
        letter = prompt_user("Select option").strip().upper()
        if letter == 'M' or (letter.isalpha() and len(letter) == 1):
            return letter
        
        error_msg = "Please enter a valid letter or 'M'"
        error_padding = (term_width - len(error_msg)) // 2
        padded_error = " " * error_padding + error_msg
        console.print(f"[red]{padded_error}[/red]")

def build_request_analysis_prompt(request: str) -> str:
    """Build prompt for information requests"""
    return CHANGE_ANALYSIS_PROMPT.format(
        request=request
    )