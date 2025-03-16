"""
Main entry point for Janito.
"""
import os
import sys
from typing import Optional
import importlib.resources
import typer
from rich.console import Console
import anthropic
from janito.config import get_config
from janito.chat_history import store_conversation, get_chat_history_context
from janito.callbacks import pre_tool_callback, post_tool_callback, text_callback
from janito.token_report import generate_token_report
from janito.tools import str_replace_editor
from janito.tools.bash import bash_tool
import claudine

app = typer.Typer()

@app.command()
def create_tool(name: str = typer.Argument(..., help="Name of the tool to create")):
    """
    Create a new tool with the given name.
    """
    console = Console()
    
    # Ensure workspace is set
    workspace_dir = get_config().workspace_dir
    
    # Create the tools directory if it doesn't exist
    tools_dir = os.path.join(workspace_dir, "tools")
    os.makedirs(tools_dir, exist_ok=True)
    
    # Create the tool file
    tool_file = os.path.join(tools_dir, f"{name}.py")
    
    # Check if the file already exists
    if os.path.exists(tool_file):
        console.print(f"[bold red]Error:[/bold red] Tool file already exists: {tool_file}")
        return
    
    # Create the tool file with a template
    template = f'''"""
{name} tool for Janito.
"""

def {name}(param1: str) -> str:
    """
    Description of the {name} tool.
    
    Args:
        param1: Description of param1
        
    Returns:
        str: Description of return value
    """
    # TODO: Implement the tool
    return f"Executed {name} with param1={{param1}}"
'''
    
    with open(tool_file, "w") as f:
        f.write(template)
    
    console.print(f"[bold green]Created tool:[/bold green] {tool_file}")

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, 
         query: Optional[str] = typer.Argument(None, help="Query to send to the claudine agent"),
         verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose mode with detailed output"),
         show_tokens: bool = typer.Option(False, "--show-tokens", "-t", help="Show detailed token usage and pricing information"),
         workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Set the workspace directory"),
         config_str: Optional[str] = typer.Option(None, "--set-config", help="Configuration string in format 'key=value', e.g., 'context=5' for number of history messages to include"),
         show_config: bool = typer.Option(False, "--show-config", help="Show current configuration")):
    """
    Janito CLI tool. If a query is provided without a command, it will be sent to the claudine agent.
    """    
    console = Console()
    
    # Set verbose mode in config
    get_config().verbose = verbose
    
    if workspace:
        try:
            print(f"Setting workspace directory to: {workspace}")
            get_config().workspace_dir = workspace
            print(f"Workspace directory set to: {get_config().workspace_dir}")
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            sys.exit(1)
            
    # Show current configuration if requested
    if show_config:
        config = get_config()
        console.print("[bold blue]Current Configuration:[/bold blue]")
        console.print(f"[bold]Workspace Directory:[/bold] {config.workspace_dir}")
        console.print(f"[bold]Verbose Mode:[/bold] {'Enabled' if config.verbose else 'Disabled'}")
        console.print(f"[bold]Chat History Context Count:[/bold] {config.history_context_count} messages")
        # Exit if this was the only operation requested
        if ctx.invoked_subcommand is None and not query:
            sys.exit(0)
            
    # Handle the --set-config parameter
    if config_str is not None:
        try:
            # Parse the config string
            if "context=" in config_str:
                context_value = config_str.split("context=")[1].strip()
                # If there are other configs after context, extract just the number
                if " " in context_value:
                    context_value = context_value.split(" ")[0]
                
                try:
                    context_value = int(context_value)
                    if context_value < 0:
                        console.print("[bold red]Error:[/bold red] History context count must be a non-negative integer")
                        return
                    
                    get_config().history_context_count = context_value
                    console.print(f"[bold green]Chat history context count set to {context_value} messages[/bold green]")
                except ValueError:
                    console.print(f"[bold red]Error:[/bold red] Invalid context value: {context_value}. Must be an integer.")
            else:
                console.print(f"[bold yellow]Warning:[/bold yellow] Unsupported configuration in: {config_str}")
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            
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
            import importlib.resources as pkg_resources
            try:
                # For Python 3.9+
                try:
                    from importlib.resources import files
                    instructions = files('janito.data').joinpath('instructions.txt').read_text(encoding='utf-8')
                # Fallback for older Python versions
                except (ImportError, AttributeError):
                    instructions = pkg_resources.read_text('janito.data', 'instructions.txt', encoding='utf-8')
            except Exception as e:
                console.print(f"[bold red]Error loading instructions:[/bold red] {str(e)}")
                instructions = "You are Janito, an AI assistant."
                
            # Temporarily disable chat history
            # Get chat history context
            # chat_history = get_chat_history_context(get_config().history_context_count)
            # if chat_history:
            #     console.print("[dim]Loaded chat history from previous sessions.[/dim]")
            #     # Append chat history to instructions
            #     instructions = f"{instructions}\n\n{chat_history}"
                   
            # Get tools
            from janito.tools import get_tools
            tools_list = get_tools()
            
            # Initialize the agent with the tools
            agent = claudine.Agent(
                api_key=api_key,
                system_prompt=instructions,
                callbacks={"pre_tool": pre_tool_callback, "post_tool": post_tool_callback, "text": text_callback},
                text_editor_tool=str_replace_editor,
               #bash_tool=bash_tool,
                tools=tools_list,
                verbose=verbose
            )
            
            # Send the query to the agent
            try:
                agent.query(query)
                
                # Temporarily disable storing conversation in chat history
                # Store the conversation in chat history
                # store_conversation(query, response, agent)
                
                # Print token usage report if show_tokens mode is enabled
                if show_tokens:
                    generate_token_report(agent, verbose=True)
                else:
                    # Show basic token usage
                    generate_token_report(agent, verbose=False)
                    
            except anthropic.APIError as e:
                console.print(f"[bold red]Anthropic API Error:[/bold red] {str(e)}")
                
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {str(e)}")
                if verbose:
                    import traceback
                    console.print(traceback.format_exc())

if __name__ == "__main__":
    app()