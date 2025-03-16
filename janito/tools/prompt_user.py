"""
Tool for prompting the user for input through the claudine agent.
"""
from typing import Tuple
from janito.tools.rich_console import print_info, print_error


def prompt_user(
    prompt_text: str,
) -> Tuple[str, bool]:
    """
    Prompt the user for input and return their response.
    
    Args:
        prompt_text: Text to display to the user as a prompt
        
    Returns:
        A tuple containing (user_response, is_error)
    """
    print_info(f"Prompting user with '{prompt_text}'", "User Prompt") 
    try:
        # Only show "Waiting for your answer:" in the input prompt
        # The original prompt is already displayed in the panel
        user_response = input("Waiting for your answer: ")
        return (user_response, False)
    except Exception as e:
        error_msg = f"Error prompting user: {str(e)}"
        print_error(error_msg, "Prompt Error")
        return (error_msg, True)