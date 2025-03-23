"""
Main CLI application for Janito.
"""
import sys
from typing import Optional
import typer
from rich.console import Console
import importlib.metadata

from janito.config import get_config
from janito.cli.commands import handle_config_commands, validate_parameters
from janito.cli.agent import handle_query
from janito.cli.utils import get_stdin_termination_hint

app = typer.Typer()
console = Console()

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, 
         query: Optional[str] = typer.Argument(None, help="Query to send to the claudine agent"),
         verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose mode with detailed output"),
         show_tokens: bool = typer.Option(False, "--show-tokens", "--tokens", help="Show detailed token usage and pricing information"),
         workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Set the workspace directory"),
         config_str: Optional[str] = typer.Option(None, "--set-config", help="Configuration string in format 'key=value', e.g., 'temperature=0.7' or 'profile=technical'"),
         show_config: bool = typer.Option(False, "--show-config", help="Show current configuration"),
         reset_config: bool = typer.Option(False, "--reset-config", help="Reset configuration by removing the config file"),
         set_api_key: Optional[str] = typer.Option(None, "--set-api-key", help="Set the Anthropic API key globally in the user's home directory"),
         ask: bool = typer.Option(False, "--ask", help="Enable ask mode which disables tools that perform changes"),
         trust: bool = typer.Option(False, "--trust", "-t", help="Enable trust mode which suppresses tool outputs for a more concise execution (per-session setting)"),
         temperature: float = typer.Option(0.0, "--temperature", help="Set the temperature for model generation (0.0 to 1.0)"),
         profile: Optional[str] = typer.Option(None, "--profile", help="Use a predefined parameter profile (precise, balanced, conversational, creative, technical)"),
         role: Optional[str] = typer.Option(None, "--role", help="Set the assistant's role (default: 'software engineer')"),
         version: bool = typer.Option(False, "--version", help="Show the version and exit"),
         continue_conversation: Optional[str] = typer.Option(None, "--continue", "-c", help="Continue a previous conversation, optionally with a specific message ID")):
    """
    Janito CLI tool. If a query is provided without a command, it will be sent to the claudine agent.
    """    
    # Set verbose mode in config
    get_config().verbose = verbose
    
    # Set ask mode in config
    get_config().ask_mode = ask
    
    # Set trust mode in config
    get_config().trust_mode = trust
    
    # Show a message if ask mode is enabled
    if ask:
        console.print("[bold yellow]⚠️ Ask Mode enabled:[/bold yellow] 🔒 Tools that perform changes are disabled")
        
    # Show a message if trust mode is enabled
    if trust:
        console.print("[bold blue]⚡ Trust Mode enabled:[/bold blue] Tool outputs are suppressed for concise execution (per-session setting)")
    
    # Show version and exit if requested
    if version:
        try:
            version_str = importlib.metadata.version("janito")
            console.print(f"🚀 Janito version: {version_str}")
        except importlib.metadata.PackageNotFoundError:
            console.print("🚀 Janito version: [italic]development[/italic]")
        sys.exit(0)
    
    # Validate temperature
    validate_parameters(temperature)
    
    # Handle configuration-related commands
    exit_after_config = handle_config_commands(
        ctx, 
        reset_config, 
        workspace, 
        show_config, 
        profile, 
        role, 
        set_api_key, 
        config_str, 
        query,
        continue_conversation
    )
    
    if exit_after_config:
        sys.exit(0)
    
    # Handle query if no subcommand was invoked
    if ctx.invoked_subcommand is None:
        # If no query provided in command line, read from stdin
        if not query:
            console.print("[bold blue]📝 No query provided in command line. Reading from stdin...[/bold blue]")
            console.print(get_stdin_termination_hint())
            query = sys.stdin.read().strip()
            
        # Only proceed if we have a query (either from command line or stdin)
        if query:
            handle_query(query, temperature, verbose, show_tokens, continue_conversation)