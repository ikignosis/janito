"""User prompts and input handling for analysis."""

from typing import List, Dict, Optional
from .options import AnalysisOption
from rich.console import Console
from rich.rule import Rule
from rich.prompt import Prompt

# Keep only prompt-related functionality
CHANGE_ANALYSIS_PROMPT = """
Considering the above workset content, provide 2 sections, each identified by a keyword and representing an option.
Each option should include a concise action plan and a list of affected files.
1st option should be simple, minimalistic, and straightforward
2nd option should be standard, allowing for greater flexibility and adaptability

Do not use style as keyword, instead focus on the changes summary.

Use the following format:

A. Keyword summary of the change
Action Plan:
- Concise steps to implement the change

Affected Files:
- path/file1.py (new)
- path/file2.py (modified)
- path/file3.py (removed)

END_OF_OPTIONS (mandatory marker)

RULES:
- validate the action plan steps against the workset file
    - if step is generic and does not match any occurrence in the workset files, do not include it in the action plan
    e.g "remove all references to xpto" (and xpto is not present in any of the workset files)
    - if step is already present in the workset file, do not include it in the action plan
    e.g. add a print statement to a file that already has a print statement
- remove any action plan items which 
- do NOT provide the content of the files
- do NOT offer to implement the changes
- description items should be 80 chars
- when removing packages do not mention the directory removal itself in the affected files

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



def build_request_analysis_prompt(request: str) -> str:
    """Build prompt for information requests"""
    return CHANGE_ANALYSIS_PROMPT.format(
        request=request
    )
