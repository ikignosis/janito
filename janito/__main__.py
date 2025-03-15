"""
Main entry point for the janito CLI.
"""

import typer
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from rich.console import Console
from rich import print as rprint
from rich.markdown import Markdown
import claudine
from claudine.exceptions import MaxTokensExceededException, MaxRoundsExceededException
import locale

# Fix console encoding for Windows
if sys.platform == 'win32':
    # Try to set UTF-8 mode for Windows 10 version 1903 or newer
    os.system('chcp 65001 > NUL')
    # Ensure stdout and stderr are using UTF-8
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    # Set locale to UTF-8
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

from janito.tools.str_replace_editor.editor import str_replace_editor
from janito.tools.find_files import find_files
from janito.tools.delete_file import delete_file
from janito.tools.search_text import search_text
from janito.config import get_config
from janito.tools.decorators import format_tool_label

app = typer.Typer(help="Janito CLI tool")

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
    
    # Try to find the tool function
    tool_func = None
    for tool in [find_files, str_replace_editor, delete_file, search_text]:
        if tool.__name__ == tool_name:
            tool_func = tool
            break
    
    # Format the tool label if possible
    label = None
    if tool_func:
        label = format_tool_label(tool_func, tool_input)
    
    if not label:
        label = f"{tool_name}"
        
        # Special handling for str_replace_editor
        if tool_name == "str_replace_editor":
            command = tool_input.get("command", "unknown")
            file_path = tool_input.get("file_path", "")
            
            if command == "view":
                label = f"Editing file: {file_path} (view)"
            elif command == "edit":
                label = f"Editing file: {file_path} (edit)"
            else:
                label = f"Editing file: {file_path} ({command})"
    
    # Print the tool call
    console.print(f"Tool Call: {label}", style="bold yellow")
    
    # For delete_file, confirm with the user
    if tool_name == "delete_file" and "file_path" in tool_input:
        file_path = tool_input["file_path"]
        
        # Get the absolute path
        abs_path = os.path.abspath(file_path)
        
        # Ask for confirmation
        console.print(f"[bold red]Warning:[/bold red] About to delete file: {abs_path}")
        confirm = typer.confirm("Are you sure you want to delete this file?", default=False)
        
        if not confirm:
            console.print("File deletion cancelled.")
            return tool_input, True  # Cancel the tool call
    
    # Return the original tool input and don't cancel
    return tool_input, False

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

@app.command()
def hello(name: str = typer.Argument("World", help="Name to greet")):
    """
    Say hello to someone.
    """
    rprint(f"[bold green]Hello {name}[/bold green]")
    
@app.command()
def claudine_info():
    """
    Show information about the claudine package.
    """
    rprint(f"[bold blue]Using claudine from:[/bold blue] {claudine.__file__}")
    if hasattr(claudine, "__version__"):
        rprint(f"[bold blue]Claudine version:[/bold blue] {claudine.__version__}")

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, 
         query: Optional[str] = typer.Argument(None, help="Query to send to the claudine agent"),
         debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
         verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed token usage and pricing information"),
         workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Set the workspace directory")):
    """
    Janito CLI tool. If a query is provided without a command, it will be sent to the claudine agent.
    """    
    console = Console()
    
    # Set debug mode in config
    get_config().debug_mode = debug
    
    if workspace:
        try:
            print(f"Setting workspace directory to: {workspace}")
            get_config().workspace_dir = workspace
            print(f"Workspace directory set to: {get_config().workspace_dir}")
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            sys.exit(1)
            
    if ctx.invoked_subcommand is None and query:
        # Get API key from environment variable or ask the user
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            console.print("[bold yellow]Warning:[/bold yellow] ANTHROPIC_API_KEY environment variable not set.")
            console.print("Please set it or provide your API key now:")
            api_key = typer.prompt("Anthropic API Key", hide_input=True)
        
        # Load instructions from file
        package_dir = Path(__file__).parent
        instructions_path = package_dir / "data" / "instructions.txt"
        try:
            with open(instructions_path, "r") as f:
                instructions = f.read().strip()
        except FileNotFoundError:
            console.print(f"[bold yellow]Warning:[/bold yellow] Instructions file not found at {instructions_path}")
            console.print("[dim]Using default instructions instead.[/dim]")
            instructions = "You are a helpful AI assistant. Answer the user's questions to the best of your ability."
               
        # Initialize the agent with the tools
        agent = claudine.Agent(
            api_key=api_key,
            tools=[
                delete_file,
                find_files,
                search_text
            ],
            text_editor_tool=str_replace_editor,
            tool_callbacks=(pre_tool_callback, post_tool_callback),
            max_tokens=4096,
            temperature=0.7,
            instructions=instructions,
            debug_mode=debug  # Enable debug mode
        )
        
        # Process the query
        console.print(f"[bold blue]Query:[/bold blue] {query}")
        console.print("[bold blue]Generating response...[/bold blue]")
        
        try:
            response = agent.process_prompt(query)
            
            console.print("\n[bold green]Response:[/bold green]")
            # Use rich's enhanced Markdown rendering for the response
            console.print(Markdown(response, code_theme="monokai"))
            
        except MaxTokensExceededException as e:
            # Display the partial response if available
            if e.response_text:
                console.print("\n[bold green]Partial Response:[/bold green]")
                console.print(Markdown(e.response_text, code_theme="monokai"))
            
            console.print("\n[bold red]Error:[/bold red] Response was truncated because it reached the maximum token limit.")
            console.print("[dim]Consider increasing the max_tokens parameter or simplifying your query.[/dim]")
            
        except MaxRoundsExceededException as e:
            # Display the final response if available
            if e.response_text:
                console.print("\n[bold green]Response:[/bold green]")
                console.print(Markdown(e.response_text, code_theme="monokai"))
            
            console.print(f"\n[bold red]Error:[/bold red] Maximum number of tool execution rounds ({e.rounds}) reached. Some tasks may be incomplete.")
            console.print("[dim]Consider increasing the max_rounds parameter or breaking down your task into smaller steps.[/dim]")
        
        # Show token usage
        usage = agent.get_token_usage()
        text_usage = usage.text_usage
        tools_usage = usage.tools_usage
        
        if verbose:
            def debug_tokens(agent):
                """
                Display detailed token usage and pricing information.
                """
                from claudine.token_tracking import MODEL_PRICING, DEFAULT_MODEL
                
                usage = agent.get_token_usage()
                text_usage = usage.text_usage
                tools_usage = usage.tools_usage
                total_usage = usage.total_usage
                
                # Get the pricing model
                pricing = MODEL_PRICING.get(DEFAULT_MODEL)
                
                # Calculate costs manually
                text_input_cost = pricing.input_tokens.calculate_cost(text_usage.input_tokens)
                text_output_cost = pricing.output_tokens.calculate_cost(text_usage.output_tokens)
                tools_input_cost = pricing.input_tokens.calculate_cost(tools_usage.input_tokens)
                tools_output_cost = pricing.output_tokens.calculate_cost(tools_usage.output_tokens)
                
                # Format costs
                format_cost = lambda cost: f"{cost * 100:.2f}¢" if cost < 1.0 else f"${cost:.6f}"
                
                console = Console()
                console.print("\n[bold blue]Detailed Token Usage:[/bold blue]")
                console.print(f"Text Input tokens: {text_usage.input_tokens}")
                console.print(f"Text Output tokens: {text_usage.output_tokens}")
                console.print(f"Text Total tokens: {text_usage.input_tokens + text_usage.output_tokens}")
                console.print(f"Tool Input tokens: {tools_usage.input_tokens}")
                console.print(f"Tool Output tokens: {tools_usage.output_tokens}")
                console.print(f"Tool Total tokens: {tools_usage.input_tokens + tools_usage.output_tokens}")
                console.print(f"Total tokens: {total_usage.input_tokens + total_usage.output_tokens}")
                
                console.print("\n[bold blue]Pricing Information:[/bold blue]")
                console.print(f"Input pricing: ${pricing.input_tokens.cost_per_million_tokens}/million tokens")
                console.print(f"Output pricing: ${pricing.output_tokens.cost_per_million_tokens}/million tokens")
                console.print(f"Text Input cost: {format_cost(text_input_cost)}")
                console.print(f"Text Output cost: {format_cost(text_output_cost)}")
                console.print(f"Text Total cost: {format_cost(text_input_cost + text_output_cost)}")
                console.print(f"Tool Input cost: {format_cost(tools_input_cost)}")
                console.print(f"Tool Output cost: {format_cost(tools_output_cost)}")
                console.print(f"Tool Total cost: {format_cost(tools_input_cost + tools_output_cost)}")
                console.print(f"Total cost: {format_cost(text_input_cost + text_output_cost + tools_input_cost + tools_output_cost)}")

                # Display per-tool breakdown if available
                if usage.by_tool:
                    console.print("\n[bold blue]Per-Tool Breakdown:[/bold blue]")
                    for tool_name, tool_usage in usage.by_tool.items():
                        tool_input_cost = pricing.input_tokens.calculate_cost(tool_usage.input_tokens)
                        tool_output_cost = pricing.output_tokens.calculate_cost(tool_usage.output_tokens)
                        console.print(f"Tool: {tool_name}")
                        console.print(f"  Input tokens: {tool_usage.input_tokens}")
                        console.print(f"  Output tokens: {tool_usage.output_tokens}")
                        console.print(f"  Total tokens: {tool_usage.input_tokens + tool_usage.output_tokens}")
                        console.print(f"  Total cost: {format_cost(tool_input_cost + tool_output_cost)}")

            debug_tokens(agent)
        else:
            console.print(f"\nTotal tokens: {text_usage.input_tokens + text_usage.output_tokens + tools_usage.input_tokens + tools_usage.output_tokens}")
            cost_info = agent.get_cost()
            if hasattr(cost_info, 'format_total_cost'):
                console.print(f"Cost: {cost_info.format_total_cost()}")

if __name__ == "__main__":
    app()
