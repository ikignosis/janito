"""
Main entry point for the janito CLI.
"""

import typer
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
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
from janito.callbacks import pre_tool_callback, post_tool_callback
from janito.token_report import generate_token_report

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
            
    if ctx.invoked_subcommand is None:
        # If no query provided in command line, read from stdin
        if not query:
            console.print("[bold blue]No query provided in command line. Reading from stdin...[/bold blue]")
            query = sys.stdin.read().strip()
            
        # Only proceed if we have a query (either from command line or stdin)
        if query:
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
            
            # Show token usage report
            generate_token_report(agent, verbose)
        else:
            console.print("[bold yellow]No query provided. Exiting.[/bold yellow]")

if __name__ == "__main__":
    app()
