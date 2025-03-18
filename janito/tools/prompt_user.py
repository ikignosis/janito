"""
Tool for prompting the user for input through the claudine agent.
"""
from typing import Tuple, List
import sys
import textwrap
from rich.console import Console
from janito.tools.rich_console import print_info, print_error, print_warning
from janito.tools.usage_tracker import track_usage
from janito.cli.utils import get_stdin_termination_hint


console = Console()

@track_usage('user_prompts')
def prompt_user(
    prompt_text: str,
) -> Tuple[str, bool]:
    """
    Prompt the user for input and return their response.
    Displays the prompt in a panel and uses stdin for input.
    
    Args:
        prompt_text: Text to display to the user as a prompt
        
    Returns:
        A tuple containing (user_response, is_error)
    """
    try:
        # Display the prompt with ASCII header
        console.print("\n" + "="*50)
        console.print("USER PROMPT")
        console.print("="*50)
        console.print(prompt_text)
        
        # Show input instructions with stdin termination hint
        termination_hint = get_stdin_termination_hint().replace("[bold yellow]", "").replace("[/bold yellow]", "")
        print_info(f"Enter your response below. {termination_hint}", "Input Instructions")
        
        # Read input from stdin
        lines = []
        for line in sys.stdin:
            lines.append(line.rstrip('\n'))
        
        # Join the lines with newlines to preserve the multiline format
        user_response = "\n".join(lines)
        
        # If no input was provided, return a message
        if not user_response.strip():
            print_warning("No input was provided.", "Empty Input")
            return ("", False)
            
        return (user_response, False)
    except Exception as e:
        error_msg = f"Error prompting user: {str(e)}"
        print_error(error_msg, "Prompt Error")
        return (error_msg, True)