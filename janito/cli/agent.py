"""
Agent initialization and query handling for Janito CLI.
"""
import os
import sys
import json
import anthropic
import claudine
import typer
from rich.console import Console
from pathlib import Path
from jinja2 import Template
import importlib.resources as pkg_resources

from janito.config import get_config, Config
from janito.callbacks import text_callback
from janito.token_report import generate_token_report
from janito.tools import str_replace_editor
from janito.tools.bash.bash import bash_tool
from janito.cli.output import display_generation_params

console = Console()

def get_api_key() -> str:
    """
    Get the API key from global config, environment variable, or user input.
    
    Returns:
        str: The API key
    """
    # Get API key from global config, environment variable, or ask the user
    api_key = Config.get_api_key()
    
    # If not found in global config, try environment variable
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        
    # If still not found, prompt the user
    if not api_key:
        console.print("[bold yellow]⚠️ Warning:[/bold yellow] API key not found in global config or ANTHROPIC_API_KEY environment variable.")
        console.print("🔑 Please set it using --set-api-key or provide your API key now:")
        api_key = typer.prompt("Anthropic API Key", hide_input=True)
    
    return api_key

def load_instructions() -> str:
    """
    Load instructions template and render it with variables.
    
    Returns:
        str: The rendered instructions
    """
    import platform
    
    try:
        # For Python 3.9+
        try:
            from importlib.resources import files
            template_content = files('janito.data').joinpath('instructions_template.txt').read_text(encoding='utf-8')
        # Fallback for older Python versions
        except (ImportError, AttributeError):
            template_content = pkg_resources.read_text('janito.data', 'instructions_template.txt', encoding='utf-8')
        
        # Create template variables
        template_variables = {
            'platform': platform.system(),
            'role': get_config().role,
            # Add any other variables you want to pass to the template here
        }
        
        # Create template and render
        template = Template(template_content)
        instructions = template.render(**template_variables)
        
    except Exception as e:
        console.print(f"[bold red]❌ Error loading instructions template:[/bold red] {str(e)}")
        # Try to fall back to regular instructions.txt
        try:
            # For Python 3.9+
            try:
                from importlib.resources import files
                instructions = files('janito.data').joinpath('instructions.txt').read_text(encoding='utf-8')
            # Fallback for older Python versions
            except (ImportError, AttributeError):
                instructions = pkg_resources.read_text('janito.data', 'instructions.txt', encoding='utf-8')
        except Exception as e2:
            console.print(f"[bold red]❌ Error loading fallback instructions:[/bold red] {str(e2)}")
            instructions = "You are Janito, an AI assistant."
    
    return instructions

def initialize_agent(temperature: float, verbose: bool) -> claudine.Agent:
    """
    Initialize the Claude agent with tools and configuration.
    
    Args:
        temperature: Temperature value for model generation
        verbose: Whether to enable verbose mode
        
    Returns:
        claudine.Agent: The initialized agent
    """
    # Get API key
    api_key = get_api_key()
    
    # Load instructions
    instructions = load_instructions()
    
    # Get tools
    from janito.tools import get_tools, reset_tracker
    tools_list = get_tools()
    
    # Reset usage tracker before each query
    reset_tracker()
    
    # Use command line parameters if provided (not default values), otherwise use config
    temp_to_use = temperature if temperature != 0.0 else get_config().temperature
    
    # Get profile parameters if a profile is set
    config = get_config()
    profile_data = None
    if config.profile:
        profile_data = config.get_available_profiles()[config.profile]
    
    # Display generation parameters if verbose mode is enabled
    if verbose:
        display_generation_params(temp_to_use, profile_data, temperature)
    
    # Create config_params dictionary with generation parameters
    config_params = {
        "temperature": temp_to_use
    }
    
    # Add top_k and top_p from profile if available
    if profile_data:
        if "top_k" in profile_data and profile_data["top_k"] != 0:
            config_params["top_k"] = profile_data["top_k"]
        if "top_p" in profile_data and profile_data["top_p"] != 0.0:
            config_params["top_p"] = profile_data["top_p"]
    
    # Initialize the agent
    agent = claudine.Agent(
        api_key=api_key,
        system_prompt=instructions,
        callbacks={"text": text_callback},
        text_editor_tool=str_replace_editor,
        bash_tool=bash_tool,
        tools=tools_list,
        verbose=verbose,
        max_tokens=8126,
        max_tool_rounds=100,
        config_params=config_params,
    )
    
    return agent

def save_messages(agent):
    """
    Save agent messages to .janito/last_message.json
    
    Args:
        agent: The claudine agent instance
    """
    try:
        # Get the workspace directory
        workspace_dir = Path(get_config().workspace_dir)
        
        # Create .janito directory if it doesn't exist
        janito_dir = workspace_dir / ".janito"
        janito_dir.mkdir(exist_ok=True)
        
        # Get messages from the agent
        messages = agent.get_messages()
        
        # Save messages to file
        with open(janito_dir / "last_message.json", "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
            
        if get_config().verbose:
            console.print(f"[bold green]✅ Conversation saved to {janito_dir / 'last_message.json'}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]❌ Error saving conversation:[/bold red] {str(e)}")

def load_messages():
    """
    Load messages from .janito/last_message.json
    
    Returns:
        List of message dictionaries or None if file doesn't exist
    """
    try:
        # Get the workspace directory
        workspace_dir = Path(get_config().workspace_dir)
        
        # Check if file exists
        messages_file = workspace_dir / ".janito" / "last_message.json"
        if not messages_file.exists():
            console.print("[bold yellow]⚠️ No previous conversation found[/bold yellow]")
            return None
        
        # Load messages from file
        with open(messages_file, "r", encoding="utf-8") as f:
            messages = json.load(f)
            
        if get_config().verbose:
            console.print(f"[bold green]✅ Loaded previous conversation from {messages_file}[/bold green]")
            console.print(f"[dim]📝 Conversation has {len(messages)} messages[/dim]")
            
        return messages
    except Exception as e:
        console.print(f"[bold red]❌ Error loading previous conversation:[/bold red] {str(e)}")
        return None

def handle_query(query: str, temperature: float, verbose: bool, show_tokens: bool, continue_conversation: bool = False) -> None:
    """
    Handle a query by initializing the agent and sending the query.
    
    Args:
        query: The query to send to the agent
        temperature: Temperature value for model generation
        verbose: Whether to enable verbose mode
        show_tokens: Whether to show detailed token usage
        continue_conversation: Whether to continue the previous conversation
    """
    # Initialize the agent
    agent = initialize_agent(temperature, verbose)
    
    # Load previous messages if continuing conversation
    if continue_conversation:
        messages = load_messages()
        if messages:
            agent.set_messages(messages)
            console.print("[bold blue]🔄 Continuing previous conversation[/bold blue]")
    
    # Send the query to the agent
    try:
        agent.query(query)
        
        # Save messages after successful query
        save_messages(agent)
        
        # Print token usage report
        if show_tokens:
            generate_token_report(agent, verbose=True, interrupted=False)
        else:
            # Show basic token usage
            generate_token_report(agent, verbose=False, interrupted=False)
        
        # Print tool usage statistics
        from janito.tools import print_usage_stats
        print_usage_stats()
            
    except KeyboardInterrupt:
        # Handle Ctrl+C by printing token and tool usage information
        console.print("\n[bold yellow]⚠️ Query interrupted by user (Ctrl+C)[/bold yellow]")
        
        # Save messages even if interrupted
        save_messages(agent)
        
        # Print token usage report (even if interrupted)
        try:
            if show_tokens:
                generate_token_report(agent, verbose=True, interrupted=True)
            else:
                # Show basic token usage
                generate_token_report(agent, verbose=False, interrupted=True)
            
            # Print tool usage statistics
            from janito.tools import print_usage_stats
            print_usage_stats()
        except Exception as e:
            console.print(f"[bold red]❌ Error generating usage report:[/bold red] {str(e)}")
            if verbose:
                import traceback
                console.print(traceback.format_exc())
        
        # Exit with non-zero status to indicate interruption
        sys.exit(130)  # 130 is the standard exit code for SIGINT
            
    except anthropic.APIError as e:
        console.print(f"[bold red]❌ Anthropic API Error:[/bold red] {str(e)}")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {str(e)}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())