"""
Callback functions for tool execution in janito.
"""

from typing import Dict, Any, Tuple, Optional, List
from rich.console import Console
from rich.markdown import Markdown

from janito.config import get_config
from janito.tools import find_files
from janito.tools.str_replace_editor.editor import str_replace_editor
from janito.tools.delete_file import delete_file
from janito.tools.search_text import search_text
from janito.tools.decorators import format_tool_label

# Note: ConsoleCallback has been removed as we're using pre_tool and post_tool callbacks directly

def pre_tool_callback(tool_name: str, tool_input: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """
    Callback function that runs before a tool is executed.
    
    Args:
        tool_name: Name of the tool being called
        tool_input: Input parameters for the tool
        
    Returns:
        Tuple of (modified tool input, whether to cancel the tool call)
    """
    console = Console()
    
    # Add debug counter only when verbose mode is enabled
    if get_config().verbose:
        if not hasattr(pre_tool_callback, "counter"):
            pre_tool_callback.counter = 1
        console.print(f"[bold green]DEBUG: Starting tool call #{pre_tool_callback.counter}[/bold green]")
        
        # Print the tool name and input
        console.print(f"[bold green]Tool:[/bold green] {tool_name}")
        console.print(f"[bold green]Input:[/bold green] {tool_input}")
    else:
        # For non-debug mode, just print a simple message
        # Find the tool function
        tool_func = None
        if tool_name == "find_files":
            tool_func = find_files
        elif tool_name == "str_replace_editor":
            tool_func = str_replace_editor
        elif tool_name == "delete_file":
            tool_func = delete_file
        elif tool_name == "search_text":
            tool_func = search_text
            
        # Format the input for display
        display_input = ""
        if "path" in tool_input:
            display_input = tool_input["path"]
        elif "file_path" in tool_input:
            display_input = tool_input["file_path"]
        
        # Print formatted tool label if available
        formatted_label = format_tool_label(tool_func, tool_input)
        if formatted_label:
            console.print("[bold cyan]  Tool:[/bold cyan]", formatted_label, end=" → ")
        else:
            console.print("[bold cyan]  Tool:[/bold cyan]", f"{tool_name} {display_input}", end=" → ")
    
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
    
    # Add debug counter only when verbose mode is enabled
    if get_config().verbose:
        if not hasattr(post_tool_callback, "counter"):
            post_tool_callback.counter = 1
        console.print(f"[bold green]DEBUG: Completed tool call #{post_tool_callback.counter}[/bold green]")
        post_tool_callback.counter += 1
    
    # Show the number of lines in the result content
    if isinstance(result, tuple) and len(result) >= 1:
        content, is_error = result
        # Define prefix icon based on is_error
        icon_prefix = "❌ " if is_error else "✅ "
        
        if isinstance(content, str):
            # Count the number of lines in the content
            line_count = content.count('\n') + 1 if content else 0
            console.print(f"{icon_prefix}{line_count} items")
        else:
            console.print(f"{icon_prefix}{content}")
    else:
        # If result is not a tuple, convert to string and count lines
        result_str = str(result)
        # Default to success icon when no error status is available
        icon_prefix = "✅ "
        line_count = result_str.count('\n') + 1 if result_str else 0
        console.print(f"{icon_prefix}{line_count} lines")
    
    return result

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
    console.print("[bold magenta]Janito:[/bold magenta] ", Markdown(text, code_theme="monokai"), end="")