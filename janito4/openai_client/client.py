"""
OpenAI client module for sending prompts to OpenAI-compatible endpoints.
"""

import os
import sys
import json
import threading
from typing import Tuple, List, Dict, Any, Optional
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import tools
try:
    from ..tooling.tools_registry import get_all_tool_schemas, get_tool_by_name
    TOOLS_AVAILABLE = True
except (ImportError, ValueError):
    try:
        # When running directly, not as a module
        from tooling.tools_registry import get_all_tool_schemas, get_tool_by_name
        TOOLS_AVAILABLE = True
    except ImportError:
        TOOLS_AVAILABLE = False
        def get_all_tool_schemas():
            return []
        def get_tool_by_name(name):
            raise NotImplementedError("Tools not available")

# Import provider configuration for base URLs
try:
    from ..provider_config import get_base_url_from_provider
    PROVIDER_CONFIG_AVAILABLE = True
except ImportError:
    try:
        from provider_config import get_base_url_from_provider
        PROVIDER_CONFIG_AVAILABLE = True
    except ImportError:
        PROVIDER_CONFIG_AVAILABLE = False
        def get_base_url_from_provider(provider: str) -> Optional[str]:
            return None


def get_env_config() -> Tuple[Optional[str], str, str]:
    """
    Retrieve required environment variables.
    
    When OPENAI_BASE_URL is not defined, attempts to determine it based on
    the OPENAI_PROVIDER environment variable (if set) or provider from config.
    
    Returns:
        Tuple of (base_url, api_key, model)
        base_url may be None for standard OpenAI API
    """
    base_url = os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    if not model:
        raise ValueError("OPENAI_MODEL environment variable is required")
    
    # If base_url is not set, try to determine it from the provider
    if not base_url and PROVIDER_CONFIG_AVAILABLE:
        provider = os.getenv("OPENAI_PROVIDER")
        if not provider:
            # Try to get provider from config - use same logic as get_active_provider in __main__
            # First check config.json (highest priority)
            try:
                from pathlib import Path
                import json
                config_path = Path.home() / ".janito" / "config.json"
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        provider = config.get("provider")
            except Exception:
                pass
            
            # If not in config.json, check auth.json for default provider
            if not provider:
                try:
                    from ..auth_config import get_default_provider
                    provider = get_default_provider()
                except ImportError:
                    try:
                        from auth_config import get_default_provider
                        provider = get_default_provider()
                    except ImportError:
                        pass
        
        if provider:
            base_url = get_base_url_from_provider(provider)
    
    return base_url, api_key, model


def _run_with_progress_bar(func, *args, **kwargs):
    """Run a function with a Rich progress bar in a separate thread."""
    result = [None]
    exception = [None]
    
    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
    
    # Create and start the thread
    thread = threading.Thread(target=target)
    thread.start()
    
    # Show progress bar while waiting
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        task = progress.add_task("Waiting for response from the API server...", total=None)
        while thread.is_alive():
            progress.update(task, advance=0.1)
            thread.join(timeout=0.1)
    
    if exception[0]:
        raise exception[0]
    return result[0]


def send_prompt(prompt: str, verbose: bool = False, previous_messages: List[Dict[str, Any]] = None, tools: Optional[List[Dict[str, Any]]] = None) -> str:
    """Send prompt to OpenAI endpoint and return response.
    
    Args:
        prompt: The user prompt to send
        verbose: If True, print model and backend info
        previous_messages: List of previous message dicts for conversation context
        tools: Optional list of tool schemas to pass. If None, uses all available tools.
               If an empty list, no tools are passed.
    """
    base_url, api_key, model = get_env_config()
    
    # Create OpenAI client - base_url can be None for standard OpenAI
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    # Get available tools if not explicitly provided
    if tools is None:
        tools_schemas = get_all_tool_schemas() if TOOLS_AVAILABLE else []
    else:
        tools_schemas = tools
    
    console = Console()

    # Print model and backend info only in verbose mode
    if verbose:
        backend = base_url if base_url else "api.openai.com"
        from rich.text import Text
        text = Text(f"----- Model: {model} | Backend: {backend}")
        text.stylize("white on blue")
        console.print(text, highlight=False)

    # Use previous messages if provided, otherwise start with the user prompt
    messages = previous_messages.copy() if previous_messages else []
    messages.append({"role": "user", "content": prompt})
    
    while True:
        # Make API call with tools if available
        if tools_schemas:
            response = _run_with_progress_bar(
                client.chat.completions.create,
                model=model,
                messages=messages,
                temperature=1.0,
                tools=tools_schemas,
                tool_choice="auto"
            )
        else:
            response = _run_with_progress_bar(
                client.chat.completions.create,
                model=model,
                messages=messages,
                temperature=1.0
            )
        
        message = response.choices[0].message
        if message.content:
            # print the message using rich markdown
            console.print(Markdown(message.content))
        
        # Check if the model wants to call a function
        if hasattr(message, 'tool_calls') and message.tool_calls:
            # Add the model's response to messages
            messages.append(message)
            
            # Process each tool call
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                try:
                    # Call the actual tool function
                    tool_function = get_tool_by_name(tool_name)
                    tool_result = tool_function(**tool_args)
                    
                    # Add the tool response to messages
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps(tool_result)
                    })
                    
                except Exception as e:
                    # Handle tool execution errors
                    error_result = {
                        "success": False,
                        "error": f"Tool execution failed: {str(e)}"
                    }
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps(error_result)
                    })
                    print(f"❌ Tool error: {tool_name} - {e}", file=sys.stderr)
            
            # Continue the loop to get the final response after tool calls
            continue
        else:
            # No more tool calls, return the final response
            # Display token usage with cyan background
            if hasattr(response, 'usage') and response.usage:
                total_tokens = response.usage.total_tokens
                from rich.text import Text
                token_text = Text(f"=== Total tokens: {total_tokens} | Messages: {len(messages)} ===")
                token_text.stylize("white on magenta")
                console.print(token_text, highlight=False)
            return message.content if message.content else ""
            
