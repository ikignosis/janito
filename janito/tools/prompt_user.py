"""
Tool for prompting the user for input through the claudine agent.
"""
from typing import Tuple
from janito.tools.decorators import tool_meta


@tool_meta(label="Prompting user with '{prompt_text}'")
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
    try:
        # Print the prompt and get user input
        user_response = input(f"{prompt_text}")
        return (user_response, False)
    except Exception as e:
        return (f"Error prompting user: {str(e)}", True)