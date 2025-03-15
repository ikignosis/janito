"""
Main entry point for the janito CLI.
"""

import typer
from rich.console import Console
from rich import print as rprint
import claudine
import os
import sys
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Callable
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
from janito.tools.create_file import create_file
from janito.tools.delete_file import delete_file
from janito.config import get_config
        
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
    
    # Print preamble text if provided
    if preamble_text:
        console.print(preamble_text)
    
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
    
    console.print(f"[bold cyan]Tool Call:[/bold cyan] {tool_name} {display_input}", end="")
    
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
    
    # For str_replace_editor, extract just the last line of the result if it's a string
    if tool_name == "str_replace_editor" and isinstance(result, tuple) and len(result) >= 1:
        content, is_error = result
        if isinstance(content, str) and '\n' in content:
            last_line = content.strip().split('\n')[-1]
            console.print(f" → {last_line}")
        else:
            console.print(f" → {content}")
    else:
        console.print(f" → {result}")
    
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
                str_replace_editor,
                create_file,
                delete_file,
                # Add more tools here as needed
            ],
            tool_callbacks=(pre_tool_callback, post_tool_callback),
            max_tokens=1024,
            temperature=0.7,
            instructions=instructions,
            debug_mode=debug
        )
        
        # Process the query
        console.print(f"[bold blue]Query:[/bold blue] {query}")
        console.print("[bold blue]Generating response...[/bold blue]")
        
        response = agent.process_prompt(query)
        console.print("\n[bold green]Response:[/bold green]")
        console.print(response)
        
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
                console.print(f"[dim]Text Input tokens: {text_usage.input_tokens}[/dim]")
                console.print(f"[dim]Text Output tokens: {text_usage.output_tokens}[/dim]")
                console.print(f"[dim]Text Total tokens: {text_usage.input_tokens + text_usage.output_tokens}[/dim]")
                console.print(f"[dim]Tool Input tokens: {tools_usage.input_tokens}[/dim]")
                console.print(f"[dim]Tool Output tokens: {tools_usage.output_tokens}[/dim]")
                console.print(f"[dim]Tool Total tokens: {tools_usage.input_tokens + tools_usage.output_tokens}[/dim]")
                console.print(f"[dim]Total tokens: {total_usage.input_tokens + total_usage.output_tokens}[/dim]")
                
                console.print("\n[bold blue]Pricing Information:[/bold blue]")
                console.print(f"[dim]Input pricing: ${pricing.input_tokens.cost_per_million_tokens}/million tokens[/dim]")
                console.print(f"[dim]Output pricing: ${pricing.output_tokens.cost_per_million_tokens}/million tokens[/dim]")
                console.print(f"[dim]Text Input cost: {format_cost(text_input_cost)}[/dim]")
                console.print(f"[dim]Text Output cost: {format_cost(text_output_cost)}[/dim]")
                console.print(f"[dim]Text Total cost: {format_cost(text_input_cost + text_output_cost)}[/dim]")
                console.print(f"[dim]Tool Input cost: {format_cost(tools_input_cost)}[/dim]")
                console.print(f"[dim]Tool Output cost: {format_cost(tools_output_cost)}[/dim]")
                console.print(f"[dim]Tool Total cost: {format_cost(tools_input_cost + tools_output_cost)}[/dim]")
                console.print(f"[dim]Total cost: {format_cost(text_input_cost + text_output_cost + tools_input_cost + tools_output_cost)}[/dim]")
                
                # Display per-tool breakdown if available
                if usage.by_tool:
                    console.print("\n[bold blue]Per-Tool Breakdown:[/bold blue]")
                    for tool_name, tool_usage in usage.by_tool.items():
                        tool_input_cost = pricing.input_tokens.calculate_cost(tool_usage.input_tokens)
                        tool_output_cost = pricing.output_tokens.calculate_cost(tool_usage.output_tokens)
                        console.print(f"[dim]Tool: {tool_name}[/dim]")
                        console.print(f"[dim]  Input tokens: {tool_usage.input_tokens}[/dim]")
                        console.print(f"[dim]  Output tokens: {tool_usage.output_tokens}[/dim]")
                        console.print(f"[dim]  Total tokens: {tool_usage.input_tokens + tool_usage.output_tokens}[/dim]")
                        console.print(f"[dim]  Total cost: {format_cost(tool_input_cost + tool_output_cost)}[/dim]")

            debug_tokens(agent)
        else:
            console.print(f"\n[dim]Total tokens: {text_usage.input_tokens + text_usage.output_tokens + tools_usage.input_tokens + tools_usage.output_tokens}[/dim]")
            cost_info = agent.get_cost()
            if hasattr(cost_info, 'format_total_cost'):
                console.print(f"[dim]Cost: {cost_info.format_total_cost()}[/dim]")

if __name__ == "__main__":
    app()
