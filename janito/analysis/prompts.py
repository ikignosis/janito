"""User prompts and input handling for analysis."""

from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.prompt import Prompt
from rich import box

# Keep only prompt-related functionality
CHANGE_ANALYSIS_PROMPT = """
Current files:
<files>
{files_content}
</files>

Considering the above current files content, provide 3 sections, each identified by a keyword and representing an option.
Each option should include a concise description and a list of affected files.
1st option should be minimalistic style change, 2nd organized style, 3rd exntensible style.
Do not use style as keyword, instead focus on the changes summaru
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

def build_request_analysis_prompt(files_content: str, request: str) -> str:
    """Build prompt for information requests"""
    return CHANGE_ANALYSIS_PROMPT.format(
        files_content=files_content,
        request=request
    )
