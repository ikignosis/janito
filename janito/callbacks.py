"""
Callback functions for tool execution in janito.
"""

from rich.console import Console
from rich.markdown import Markdown

from janito.config import get_config

# Counter for pre-tool callbacks
pre_tool_callbacks = 0

def text_callback(text: str) -> None:
    """
    Callback function that handles text output from the agent.
    
    Args:
        text: Text output from the agent
        
    Returns:
        None
    """
    console = Console()
    
    # Add debug counter only when debug mode is enabled
    if get_config().debug_mode:
        if not hasattr(text_callback, "counter"):
            text_callback.counter = 1
        console.print(f"[bold blue]DEBUG: Text callback #{text_callback.counter}[/bold blue]")
        text_callback.counter += 1
    
    # Print the text with markdown formatting
    console.print(Markdown(text, code_theme="monokai"), end="")

