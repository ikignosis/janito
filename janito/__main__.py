"""
Main entry point for Janito.
"""
import os
import sys
from typing import Optional
import typer
from rich.console import Console
import anthropic
from pathlib import Path
from janito.config import get_config, Config
from janito.callbacks import text_callback
from janito.token_report import generate_token_report
from janito.tools import str_replace_editor
from janito.tools.bash.bash import bash_tool
import claudine
import importlib.metadata

app = typer.Typer()



@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, 
         query: Optional[str] = typer.Argument(None, help="Query to send to the claudine agent"),
         verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose mode with detailed output"),
         show_tokens: bool = typer.Option(False, "--show-tokens", "-t", help="Show detailed token usage and pricing information"),
         workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Set the workspace directory"),
         config_str: Optional[str] = typer.Option(None, "--set-config", help="Configuration string in format 'key=value', e.g., 'temperature=0.7' or 'profile=technical'"),
         show_config: bool = typer.Option(False, "--show-config", help="Show current configuration"),
         reset_config: bool = typer.Option(False, "--reset-config", help="Reset configuration by removing the config file"),
         set_api_key: Optional[str] = typer.Option(None, "--set-api-key", help="Set the Anthropic API key globally in the user's home directory"),
         ask: bool = typer.Option(False, "--ask", help="Enable ask mode which disables tools that perform changes"),
         temperature: float = typer.Option(0.0, "--temperature", help="Set the temperature for model generation (0.0 to 1.0)"),
         top_k: int = typer.Option(0, "--top-k", help="Set the top_k parameter for model generation (0 or higher, 0 to disable)"),
         top_p: float = typer.Option(0.0, "--top-p", help="Set the top_p parameter for model generation (0.0 to 1.0, 0.0 to disable)"),
         profile: Optional[str] = typer.Option(None, "--profile", help="Use a predefined parameter profile (precise, balanced, conversational, creative, technical)"),
         role: Optional[str] = typer.Option(None, "--role", help="Set the assistant's role (default: 'software engineer')"),
         version: bool = typer.Option(False, "--version", help="Show the version and exit")):
    """
    Janito CLI tool. If a query is provided without a command, it will be sent to the claudine agent.
    """    
    console = Console()
    
    # Set verbose mode in config
    get_config().verbose = verbose
    
    # Set ask mode in config
    get_config().ask_mode = ask
    
    # Validate temperature, top_k, and top_p but don't save them to config when passed as command line options
    try:
        if temperature < 0.0 or temperature > 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")
        if top_k < 0:
            raise ValueError("top_k must be a non-negative integer")
        if top_p < 0.0 or top_p > 1.0:
            raise ValueError("top_p must be between 0.0 and 1.0")
            
        # We'll use these values directly in the agent initialization but we don't save them to config
        if temperature != 0.0:
            console.print(f"[bold blue]Using temperature: {temperature} (from command line)[/bold blue]")
        if top_k != 0:
            console.print(f"[bold blue]Using top_k: {top_k} (from command line)[/bold blue]")
        if top_p != 0.0:
            console.print(f"[bold blue]Using top_p: {top_p} (from command line)[/bold blue]")
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)
    
    # Show a message if ask mode is enabled
    if ask:
        console.print("[bold yellow]Ask Mode enabled:[/bold yellow] Tools that perform changes are disabled")
    
    # Show version and exit if requested
    if version:
        try:
            version_str = importlib.metadata.version("janito")
            console.print(f"Janito version: {version_str}")
        except importlib.metadata.PackageNotFoundError:
            console.print("Janito version: [italic]development[/italic]")
        sys.exit(0)
    
    # Reset configuration if requested
    if reset_config:
        try:
            config_path = Path(get_config().workspace_dir) / ".janito" / "config.json"
            if get_config().reset_config():
                console.print(f"[bold green]Configuration file removed: {config_path}[/bold green]")
            else:
                console.print(f"[bold yellow]Configuration file does not exist: {config_path}[/bold yellow]")
        except Exception as e:
            console.print(f"[bold red]Error removing configuration file:[/bold red] {str(e)}")
        
        # Exit after resetting config
        if ctx.invoked_subcommand is None and not query:
            sys.exit(0)
    
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
        console.print(f"[bold]Local Configuration File:[/bold] .janito/config.json")
        console.print(f"[bold]Global Configuration File:[/bold] {Path.home() / '.janito' / 'config.json'}")
        
        # Show API key status
        api_key_global = Config.get_api_key()
        api_key_env = os.environ.get("ANTHROPIC_API_KEY")
        if api_key_global:
            console.print(f"[bold]API Key:[/bold] [green]Set in global config[/green]")
        elif api_key_env:
            console.print(f"[bold]API Key:[/bold] [yellow]Set in environment variable[/yellow]")
        else:
            console.print(f"[bold]API Key:[/bold] [red]Not set[/red]")
            
        console.print(f"[bold]Verbose Mode:[/bold] {'Enabled' if config.verbose else 'Disabled'}")
        console.print(f"[bold]Ask Mode:[/bold] {'Enabled' if config.ask_mode else 'Disabled'}")

        console.print(f"[bold]Role:[/bold] {config.role}")
        
        # Show profile information if one is set
        if config.profile:
            profile_data = config.get_available_profiles()[config.profile]
            console.print(f"[bold]Active Profile:[/bold] {config.profile} - {profile_data['description']}")
            
        console.print(f"[bold]Temperature:[/bold] {config.temperature}")
        console.print(f"[bold]Top K:[/bold] {config.top_k}")
        console.print(f"[bold]Top P:[/bold] {config.top_p}")
        
        # Show available profiles
        profiles = config.get_available_profiles()
        if profiles:
            console.print("\n[bold blue]Available Parameter Profiles:[/bold blue]")
            for name, data in profiles.items():
                console.print(f"[bold]{name}[/bold] (temp={data['temperature']}, top_p={data['top_p']}, top_k={data['top_k']})")
                console.print(f"  {data['description']}")
            
        # Exit if this was the only operation requested
        if ctx.invoked_subcommand is None and not query:
            sys.exit(0)
            
    # Handle the --profile parameter
    if profile is not None:
        try:
            # Apply profile without saving to config
            config = get_config()
            profile_data = config.get_available_profiles()[profile.lower()]
            
            # Set values directly without saving
            config._temperature = profile_data["temperature"]
            config._top_p = profile_data["top_p"]
            config._top_k = profile_data["top_k"]
            config._profile = profile.lower()
            
            console.print(f"[bold green]Profile '{profile.lower()}' applied for this session only[/bold green]")
            console.print(f"[dim]Description: {profile_data['description']}[/dim]")
            console.print(f"[dim]Parameters: temperature={profile_data['temperature']}, top_p={profile_data['top_p']}, top_k={profile_data['top_k']}[/dim]")
            # Exit after applying profile
            if ctx.invoked_subcommand is None and not query:
                sys.exit(0)
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            sys.exit(1)
            
    # Handle the --role parameter
    if role is not None:
        try:
            # Set role directly without saving to config
            config = get_config()
            config._role = role
            
            console.print(f"[bold green]Role '{role}' applied for this session only[/bold green]")
            # Exit after applying role
            if ctx.invoked_subcommand is None and not query:
                sys.exit(0)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            sys.exit(1)
            
    # Handle the --set-api-key parameter
    if set_api_key is not None:
        try:
            # Using the already imported Config class from line 11
            Config.set_api_key(set_api_key)
            console.print(f"[bold green]API key saved to global configuration[/bold green]")
            console.print(f"[dim]Location: {Path.home() / '.janito' / 'config.json'}[/dim]")
            # Exit after setting API key
            if ctx.invoked_subcommand is None and not query:
                sys.exit(0)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            sys.exit(1)
            
    # Handle the --set-config parameter
    if config_str is not None:
        try:
            
            # Parse the config string
            config_parts = config_str.split("=", 1)
            if len(config_parts) != 2:
                console.print(f"[bold red]Error:[/bold red] Invalid configuration format. Use 'key=value' format.")
                return
                
            key = config_parts[0].strip()
            value = config_parts[1].strip()
            
            # Remove quotes if present
            if (value.startswith("'") and value.endswith("'")) or \
               (value.startswith('"') and value.endswith('"')):
                value = value[1:-1]
                
            # Chat history context configuration has been removed
            elif key == "profile":
                try:
                    get_config().set_profile(value)
                    profile_data = get_config().get_available_profiles()[value.lower()]
                    console.print(f"[bold green]Profile set to '{value.lower()}'[/bold green]")
                    console.print(f"[dim]Description: {profile_data['description']}[/dim]")
                    console.print(f"[dim]Parameters: temperature={profile_data['temperature']}, top_p={profile_data['top_p']}, top_k={profile_data['top_k']}[/dim]")
                except ValueError as e:
                    console.print(f"[bold red]Error:[/bold red] {str(e)}")
            elif key == "temperature":
                try:
                    temp_value = float(value)
                    if temp_value < 0.0 or temp_value > 1.0:
                        console.print("[bold red]Error:[/bold red] Temperature must be between 0.0 and 1.0")
                        return
                    
                    get_config().temperature = temp_value
                    console.print(f"[bold green]Temperature set to {temp_value} and saved to configuration[/bold green]")
                except ValueError:
                    console.print(f"[bold red]Error:[/bold red] Invalid temperature value: {value}. Must be a float between 0.0 and 1.0.")
            elif key == "top_k":
                try:
                    top_k_value = int(value)
                    if top_k_value < 0:
                        console.print("[bold red]Error:[/bold red] top_k must be a non-negative integer")
                        return
                    
                    get_config().top_k = top_k_value
                    console.print(f"[bold green]top_k set to {top_k_value} and saved to configuration[/bold green]")
                except ValueError:
                    console.print(f"[bold red]Error:[/bold red] Invalid top_k value: {value}. Must be a non-negative integer.")
            elif key == "top_p":
                try:
                    top_p_value = float(value)
                    if top_p_value < 0.0 or top_p_value > 1.0:
                        console.print("[bold red]Error:[/bold red] top_p must be between 0.0 and 1.0")
                        return
                    
                    get_config().top_p = top_p_value
                    console.print(f"[bold green]top_p set to {top_p_value} and saved to configuration[/bold green]")
                except ValueError:
                    console.print(f"[bold red]Error:[/bold red] Invalid top_p value: {value}. Must be a float between 0.0 and 1.0.")
            elif key == "role":
                get_config().role = value
                console.print(f"[bold green]Role set to '{value}' and saved to configuration[/bold green]")
            else:
                console.print(f"[bold yellow]Warning:[/bold yellow] Unsupported configuration key: {key}")
            
            # Exit after applying config changes
            if ctx.invoked_subcommand is None and not query:
                sys.exit(0)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            
    if ctx.invoked_subcommand is None:
        # If no query provided in command line, read from stdin
        if not query:
            console.print("[bold blue]No query provided in command line. Reading from stdin...[/bold blue]")
            query = sys.stdin.read().strip()
            
        # Only proceed if we have a query (either from command line or stdin)
        if query:
            # Get API key from global config, environment variable, or ask the user
            api_key = Config.get_api_key()
            
            # If not found in global config, try environment variable
            if not api_key:
                api_key = os.environ.get("ANTHROPIC_API_KEY")
                
            # If still not found, prompt the user
            if not api_key:
                console.print("[bold yellow]Warning:[/bold yellow] API key not found in global config or ANTHROPIC_API_KEY environment variable.")
                console.print("Please set it using --set-api-key or provide your API key now:")
                api_key = typer.prompt("Anthropic API Key", hide_input=True)
        
            # Load instructions from file and process as a template
            import importlib.resources as pkg_resources
            import platform
            from jinja2 import Template
            
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
                    'role': get_config().role
                    # Add any other variables you want to pass to the template here
                }
                
                # Create template and render
                template = Template(template_content)
                instructions = template.render(**template_variables)
                
            except Exception as e:
                console.print(f"[bold red]Error loading instructions template:[/bold red] {str(e)}")
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
                    console.print(f"[bold red]Error loading fallback instructions:[/bold red] {str(e2)}")
                    instructions = "You are Janito, an AI assistant."
                
            # Chat history context feature has been removed
                   
            # Get tools
            from janito.tools import get_tools, reset_tracker
            tools_list = get_tools()
            
            # Reset usage tracker before each query
            reset_tracker()
            
            # Initialize the agent with the tools
            # Use command line parameters if provided (not default values), otherwise use config
            temp_to_use = temperature if temperature != 0.0 else get_config().temperature
            top_k_to_use = top_k if top_k != 0 else get_config().top_k
            top_p_to_use = top_p if top_p != 0.0 else get_config().top_p
            
            if verbose:
                # Show profile information if one is active
                config = get_config()
                if config.profile and not profile and temperature == 0.0 and top_k == 0 and top_p == 0.0:
                    profile_data = config.get_available_profiles()[config.profile]
                    console.print(f"[dim]Using profile: {config.profile} - {profile_data['description']}[/dim]")
                
                if temperature != 0.0:
                    console.print(f"[dim]Using temperature: {temp_to_use} (from command line)[/dim]")
                else:
                    console.print(f"[dim]Using temperature: {temp_to_use} (from configuration){' (via profile)' if config.profile else ''}[/dim]")
                    
                if top_k != 0:
                    console.print(f"[dim]Using top_k: {top_k_to_use} (from command line)[/dim]")
                elif top_k_to_use != 0:
                    console.print(f"[dim]Using top_k: {top_k_to_use} (from configuration){' (via profile)' if config.profile else ''}[/dim]")
                    
                if top_p != 0.0:
                    console.print(f"[dim]Using top_p: {top_p_to_use} (from command line)[/dim]")
                elif top_p_to_use != 0.0:
                    console.print(f"[dim]Using top_p: {top_p_to_use} (from configuration){' (via profile)' if config.profile else ''}[/dim]")
            
            # Create config_params dictionary with generation parameters
            config_params = {
                "temperature": temp_to_use
            }
            
            # Only add non-zero values for top_k and top_p
            if top_k_to_use != 0:
                config_params["top_k"] = top_k_to_use
            if top_p_to_use != 0.0:
                config_params["top_p"] = top_p_to_use
            
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
            
            # Send the query to the agent
            try:
                agent.query(query)
                
                # Chat history storage feature has been removed
                
                # Print token usage report if show_tokens mode is enabled
                if show_tokens:
                    generate_token_report(agent, verbose=True)
                else:
                    # Show basic token usage
                    generate_token_report(agent, verbose=False)
                
                # Print tool usage statistics
                from janito.tools import print_usage_stats
                print_usage_stats()
                    
            except anthropic.APIError as e:
                console.print(f"[bold red]Anthropic API Error:[/bold red] {str(e)}")
                
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {str(e)}")
                if verbose:
                    import traceback
                    console.print(traceback.format_exc())

if __name__ == "__main__":
    app()