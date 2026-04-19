"""
OpenAI client module for sending prompts to OpenAI-compatible endpoints.
"""

import os
import sys
import json
import logging
import threading
from typing import Tuple, List, Dict, Any, Optional
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

# Configure logger for this module
logger = logging.getLogger(__name__)

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

# Import MCP manager
try:
    from ..mcp_manager import get_mcp_manager, shutdown_mcp_manager
    MCP_MANAGER_AVAILABLE = True
except ImportError:
    MCP_MANAGER_AVAILABLE = False
    def get_mcp_manager():
        return None
    def shutdown_mcp_manager():
        pass

# Import provider configuration for base URLs
try:
    from ..provider_config import get_base_url_from_provider, is_custom_provider, CUSTOM_ENDPOINT_MARKER
    PROVIDER_CONFIG_AVAILABLE = True
except ImportError:
    try:
        from provider_config import get_base_url_from_provider, is_custom_provider, CUSTOM_ENDPOINT_MARKER
        PROVIDER_CONFIG_AVAILABLE = True
    except ImportError:
        PROVIDER_CONFIG_AVAILABLE = False
        def get_base_url_from_provider(provider: str) -> Optional[str]:
            return None
        def is_custom_provider(provider: str) -> bool:
            return False
        CUSTOM_ENDPOINT_MARKER = "CUSTOM_ENDPOINT"

# Import general configuration handling
from janito.general_config import (
    load_provider_from_config, 
    load_context_window_size, 
    load_endpoint_from_config,
    get_config_value
)


def get_env_config() -> Tuple[Optional[str], str, str]:
    """
    Retrieve required environment variables.
    
    When OPENAI_BASE_URL is not defined, attempts to determine it based on
    the OPENAI_PROVIDER environment variable (if set) or provider from config.
    
    For 'custom' provider, the endpoint must be provided via --endpoint,
    OPENAI_BASE_URL environment variable, or 'endpoint' key in config.json.
    
    Returns:
        Tuple of (base_url, api_key, model)
        base_url may be None for standard OpenAI API
    """
    base_url = os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL")
    
    logger.debug(f"Environment config loaded: base_url={base_url}, model={model}")
    
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable is required")
        raise ValueError("OPENAI_API_KEY environment variable is required")
    if not model:
        logger.error("OPENAI_MODEL environment variable is required or --set model")
        raise ValueError("OPENAI_MODEL environment variable is required or --set model")
    
    # If base_url is not set, try to determine it from the provider
    if not base_url:
        # Check provider from config, then auth.json
        provider = load_provider_from_config()
        logger.debug(f"Provider from config: {provider}")
        
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
            logger.debug(f"Base URL from provider '{provider}': {base_url}")
            
            # Handle custom provider: requires explicit endpoint
            if is_custom_provider(provider) and base_url == CUSTOM_ENDPOINT_MARKER:
                # Try to get endpoint from config
                config_endpoint = load_endpoint_from_config()
                if config_endpoint:
                    base_url = config_endpoint
                    logger.debug(f"Using endpoint from config: {base_url}")
                else:
                    # No endpoint found - this will be caught by validation
                    logger.warning("Custom provider selected but no endpoint configured")
                    base_url = None
    
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


def _is_mcp_tool(tool_name: str) -> bool:
    """Check if a tool name is an MCP tool (has service_ prefix)."""
    # MCP tools are prefixed with their service name
    # We check if the tool name starts with any known service prefix
    mcp_manager = get_mcp_manager()
    if mcp_manager:
        service = mcp_manager.get_service_for_tool(tool_name)
        return service is not None
    return False


def send_prompt(prompt: str, verbose: bool = False, previous_messages: List[Dict[str, Any]] = None, tools: Optional[List[Dict[str, Any]]] = None, use_mcp: bool = True) -> str:
    """Send prompt to OpenAI endpoint and return response.
    
    Args:
        prompt: The user prompt to send
        verbose: If True, print model and backend info
        previous_messages: List of previous message dicts for conversation context
        tools: Optional list of tool schemas to pass. If None, uses all available tools.
               If an empty list, no tools are passed.
        use_mcp: If True, load and use MCP tools (default True)
    """
    logger.info(f"Sending prompt to API")
    base_url, api_key, model = get_env_config()
    
    # Create OpenAI client - base_url can be None for standard OpenAI
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    logger.debug(f"OpenAI client created with base_url={base_url}")
    
    # Initialize MCP manager and load services if enabled
    mcp_manager = None
    if use_mcp and MCP_MANAGER_AVAILABLE:
        mcp_manager = get_mcp_manager()
        try:
            mcp_manager.load_services()
            mcp_tools = mcp_manager.get_all_tools()
            logger.info(f"Loaded {len(mcp_tools)} MCP tools from {len(mcp_manager.connected_services)} services")
        except Exception as e:
            logger.warning(f"Failed to load MCP tools: {e}")
            mcp_tools = []
    else:
        mcp_tools = []
    
    # Get available tools if not explicitly provided
    if tools is None:
        # Merge built-in tools with MCP tools
        built_in_tools = get_all_tool_schemas() if TOOLS_AVAILABLE else []
        tools_schemas = built_in_tools + mcp_tools
        logger.debug(f"Using {len(built_in_tools)} built-in tools + {len(mcp_tools)} MCP tools")
    else:
        tools_schemas = tools
        logger.debug(f"Using {len(tools_schemas)} provided tools")
    
    logger.debug(f"Using {len(tools_schemas)} tools total")
    
    # Load context window size from general config if set
    context_window_size = load_context_window_size()
    
    # Check for preserve_thinking in config
    preserve_thinking = get_config_value("preserve_thinking")
    if preserve_thinking is not None:
        logger.debug(f"Using preserve_thinking from config: {preserve_thinking}")
        
    console = Console()

    # Print model and backend info only in verbose mode
    if verbose:
        backend = base_url if base_url else "api.openai.com"
        from rich.text import Text
        text = Text(f"----- Model: {model} | Backend: {backend}")
        text.stylize("white on blue")
        console.print(text, highlight=False)
        
        # Show MCP status in verbose mode
        if mcp_manager and mcp_manager.connected_services:
            services_text = Text(f"----- MCP Services: {', '.join(mcp_manager.connected_services)}")
            services_text.stylize("white on green")
            console.print(services_text, highlight=False)

    # Use previous messages if provided, otherwise start with the user prompt
    messages = previous_messages if previous_messages else []
    messages.append({"role": "user", "content": prompt})
    
    logger.debug(f"Starting message loop with {len(messages)} messages")
    
    while True:
        # Build the base call parameters
        call_kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 1.0,
        }
        
        # Add max_tokens if context window size is set in config
        if context_window_size is not None:
            if model.startswith("gpt-5"):
                call_kwargs["max_completion_tokens"] = context_window_size
            else:
                call_kwargs["max_tokens"] = context_window_size

        # Pass preserve_thinking in extra_body if defined in config
        if preserve_thinking is not None:
            if "extra_body" not in call_kwargs:
                call_kwargs["extra_body"] = {}
            call_kwargs["extra_body"]["preserve_thinking"] = preserve_thinking

        # Make API call with tools if available
        if tools_schemas:
            logger.debug(f"Calling API with {len(tools_schemas)} tools")
            response = _run_with_progress_bar(
                client.chat.completions.create,
                **call_kwargs,
                tools=tools_schemas,
                tool_choice="auto"
            )
        else:
            logger.debug("Calling API without tools")
            response = _run_with_progress_bar(
                client.chat.completions.create,
                **call_kwargs
            )
        
        logger.debug("API response received")
        
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
                
                logger.info(f"Tool call: {tool_name}({tool_args})")
                
                # Check if this is an MCP tool
                is_mcp = _is_mcp_tool(tool_name)
                
                try:
                    if is_mcp and mcp_manager:
                        # Route to MCP manager
                        logger.debug(f"Routing MCP tool call: {tool_name}")
                        tool_result = mcp_manager.call_tool(tool_name, tool_args)
                        logger.info(f"MCP tool {tool_name} completed successfully")
                    else:
                        # Route to built-in tool
                        tool_function = get_tool_by_name(tool_name)
                        logger.debug(f"Executing built-in tool: {tool_name}")
                        tool_result = tool_function(**tool_args)
                        logger.info(f"Tool {tool_name} completed successfully")
                    
                    # Add the tool response to messages
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps(tool_result)
                    })
                    
                except Exception as e:
                    logger.error(f"Tool {tool_name} failed: {e}")
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
                    print(f"\u274c Tool error: {tool_name} - {e}", file=sys.stderr)
            
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
                logger.info(f"Request completed: {total_tokens} tokens, {len(messages)} messages")
            return message.content if message.content else ""
            
