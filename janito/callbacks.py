"""
Callback functions for tool execution in janito.
"""

from typing import Dict, Any, Tuple
from rich.console import Console
from rich.markdown import Markdown

from janito.config import get_config
from janito.tools import find_files
from janito.tools.str_replace_editor.editor import str_replace_editor
from janito.tools.delete_file import delete_file
from janito.tools.search_text import search_text
from janito.tools.decorators import format_tool_label

def pre_tool_callback(tool_name: str, tool_input: Dict[str, Any], preamble_text: str = "") -> Tuple[Dict[str, Any], bool]:
    """
    Callback function that runs before a tool is executed.
    
    Args:
        tool_name: Name of the tool being called
        tool_input: Input parameters for the tool
        preamble_text: Any text generated before the tool call
        
    Returns:
        Tuple of (modified tool input, whether to cancel the tool call)
    """
    console = Console()
    
    # Add debug counter only when debug mode is enabled
    if get_config().debug_mode:
        if not hasattr(pre_tool_callback, "counter"):
            pre_tool_callback.counter = 1
        console.print(f"[bold yellow]DEBUG: Starting tool call #{pre_tool_callback.counter}[/bold yellow]")
        pre_tool_callback.counter += 1
    
    # Print preamble text with enhanced markdown support if provided
    if preamble_text:
        console.print(Markdown(preamble_text, code_theme="monokai"))
    
    # Try to find the tool function
    tool_func = None
    for tool in [find_files, str_replace_editor, delete_file, search_text]:
        if tool.__name__ == tool_name:
            tool_func = tool
            break
    
    # Create a copy of tool_input to modify for display
    display_input = {}
    
    # Maximum length for string values
    max_length = 50
    
    # Trim long string values for display
    for key, value in tool_input.items():
        if isinstance(value, str) and len(value) > max_length:
            # For long strings, show first and last part with ellipsis in between
            display_input[key] = f"{value[:20]}...{value[-20:]}" if len(value) > 45 else value[:max_length] + "..."
        else:
            display_input[key] = value
    
    # If we found the tool and it has a tool_meta label, use that for display
    if tool_func:
        formatted_label = format_tool_label(tool_func, tool_input)
        if formatted_label:
            console.print(f"[bold cyan]Tool Call:[/bold cyan] {formatted_label}", end=" → ")
        else:
            console.print(f"[bold cyan]Tool Call:[/bold cyan] {tool_name} {display_input}", end=" → ")
    else:
        console.print(f"[bold cyan]Tool Call:[/bold cyan] {tool_name} {display_input}", end=" → ")
    
    return tool_input, True  # Continue with the tool call

def post_tool_callback(tool_name: str, tool_input: Dict[str, Any], result: Any) -> Any:
    """
    Callback function that runs after a tool is executed.
    
    Args:
        tool_name: Name of the tool that was called
        tool_input: Input parameters for the tool
        result: Result of the tool call
        
    Returns:
        Modified result
    """
    console = Console()
    
    # Add debug counter only when debug mode is enabled
    if get_config().debug_mode:
        if not hasattr(post_tool_callback, "counter"):
            post_tool_callback.counter = 1
        console.print(f"[bold green]DEBUG: Completed tool call #{post_tool_callback.counter}[/bold green]")
        post_tool_callback.counter += 1
    
    # Extract the last line of the result
    if isinstance(result, tuple) and len(result) >= 1:
        content, is_error = result
        if isinstance(content, str):
            # For find_files, extract just the count from the last line
            if tool_name == "find_files" and content.count("\n") > 0:
                lines = content.strip().split('\n')
                if lines and lines[-1].isdigit():
                    console.print(f"{lines[-1]}")
                else:
                    # Get the last line
                    last_line = content.strip().split('\n')[-1]
                    console.print(f"{last_line}")
            else:
                # For other tools, just get the last line
                if '\n' in content:
                    last_line = content.strip().split('\n')[-1]
                    console.print(f"{last_line}")
                else:
                    console.print(f"{content}")
        else:
            console.print(f"{content}")
    else:
        # If result is not a tuple, convert to string and get the last line
        result_str = str(result)
        if '\n' in result_str:
            last_line = result_str.strip().split('\n')[-1]
            console.print(f"{last_line}")
        else:
            console.print(f"{result_str}")
    
    return result