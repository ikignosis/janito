"""
Tool for prompting the user for input through the claudine agent.
"""
from typing import Tuple, List
import textwrap
from janito.tools.rich_console import print_info, print_error, print_warning
from janito.tools.usage_tracker import track_usage


@track_usage('user_prompts')
def prompt_user(
    prompt_text: str,
) -> Tuple[str, bool]:
    """
    Prompt the user for input and return their response.
    Supports multiline input - user can enter multiple lines and end input with 'END' on a new line.
    
    Args:
        prompt_text: Text to display to the user as a prompt
        
    Returns:
        A tuple containing (user_response, is_error)
    """
    print_info(f"Prompting user with '{prompt_text}'", "User Prompt")
    print_info("For multiline input, enter your text and type 'END' on a new line when finished.", "Input Instructions")
    
    try:
        lines: List[str] = []
        print("Waiting for your answer (type 'END' on a new line to finish multiline input):")
        
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        
        # If no lines were entered before END, try to get at least one line
        if not lines:
            print_warning("No input detected. Please provide at least one line:", "Empty Input")
            user_response = input()
            return (user_response, False)
        
        # Join the lines with newlines to preserve the multiline format
        user_response = "\n".join(lines)
        return (user_response, False)
    except Exception as e:
        error_msg = f"Error prompting user: {str(e)}"
        print_error(error_msg, "Prompt Error")
        return (error_msg, True)