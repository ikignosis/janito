"""
CLI functionality for the janito tool.
"""

import os
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich import print as rprint
import claudine
from claudine.exceptions import MaxTokensExceededException, MaxRoundsExceededException

from janito.config import get_config
from janito.tools import find_files
from janito.tools.str_replace_editor.editor import str_replace_editor
from janito.tools.delete_file import delete_file
from janito.tools.search_text import search_text
from janito.callbacks import pre_tool_callback, post_tool_callback

app = typer.Typer(help="Janito CLI tool")

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

def debug_tokens(agent):
    """
    Display detailed token usage and pricing information.
    """
    from claudine.token_tracking import MODEL_PRICING, DEFAULT_MODEL
    
    console = Console()
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
            console.print(f"   Tool: {tool_name}")
            console.print(f"  Input tokens: {tool_usage.input_tokens}")
            console.print(f"  Output tokens: {tool_usage.output_tokens}")
            console.print(f"  Total tokens: {tool_usage.input_tokens + tool_usage.output_tokens}")
            console.print(f"  Total cost: {format_cost(tool_input_cost + tool_output_cost)}")

def process_query(query: str, debug: bool, verbose: bool):
    """
    Process a query using the claudine agent.
    """
    console = Console()
    
    # Get API key from environment variable or ask the user
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[bold yellow]Warning:[/bold yellow] ANTHROPIC_API_KEY environment variable not set.")
        console.print("Please set it or provide your API key now:")
        api_key = typer.prompt("Anthropic API Key", hide_input=True)
    
    # Load instructions from file
    import importlib.resources as pkg_resources
    try:
        # For Python 3.9+
        try:
            from importlib.resources import files
            instructions = files('janito.data').joinpath('instructions.txt').read_text()
        # Fallback for older Python versions
        except (ImportError, AttributeError):
            instructions = pkg_resources.read_text('janito.data', 'instructions.txt')
        instructions = instructions.strip()
    except Exception as e:
        console.print(f"[bold yellow]Warning:[/bold yellow] Could not load instructions file: {str(e)}")
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
        
        console.print("\n[bold magenta]Janito:[/bold magenta] ", end="")
        # Use rich's enhanced Markdown rendering for the response
        console.print(Markdown(response, code_theme="monokai"))
        
    except MaxTokensExceededException as e:
        # Display the partial response if available
        if e.response_text:
            console.print("\n[bold magenta]Janito:[/bold magenta] ", end="")
            console.print(Markdown(e.response_text, code_theme="monokai"))
        
        console.print("\n[bold red]Error:[/bold red] Response was truncated because it reached the maximum token limit.")
        console.print("[dim]Consider increasing the max_tokens parameter or simplifying your query.[/dim]")
        
    except MaxRoundsExceededException as e:
        # Display the final response if available
        if e.response_text:
            console.print("\n[bold magenta]Janito:[/bold magenta] ", end="")
            console.print(Markdown(e.response_text, code_theme="monokai"))
        
        console.print(f"\n[bold red]Error:[/bold red] Maximum number of tool execution rounds ({e.rounds}) reached. Some tasks may be incomplete.")
        console.print("[dim]Consider increasing the max_rounds parameter or breaking down your task into smaller steps.[/dim]")
    
    # Show token usage
    usage = agent.get_token_usage()
    text_usage = usage.text_usage
    tools_usage = usage.tools_usage
    
    if verbose:
        debug_tokens(agent)
    else:
        total_tokens = text_usage.input_tokens + text_usage.output_tokens + tools_usage.input_tokens + tools_usage.output_tokens
        cost_info = agent.get_cost()
        cost_display = cost_info.format_total_cost() if hasattr(cost_info, 'format_total_cost') else ""
        # Consolidated tokens and cost in a single line with a ruler
        console.print(Rule(f"Tokens: {total_tokens} | Cost: {cost_display}", style="dim", align="center"))

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
        process_query(query, debug, verbose)