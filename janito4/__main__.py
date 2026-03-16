#!/usr/bin/env python3
"""
OpenAI CLI - A simple command-line interface to interact with OpenAI-compatible endpoints.

This CLI uses environment variables for configuration:
- OPENAI_BASE_URL: The base URL of the OpenAI-compatible API endpoint (optional for standard OpenAI)
- OPENAI_API_KEY: The API key for authentication
- OPENAI_MODEL: The model name to use for completions

The CLI includes function calling tools that can be used by the AI model.

Usage:
    python -m janito4 "Your prompt here"    # Single prompt mode
    echo "Your prompt" | python -m janito4 # Pipe input mode
    python -m janito4                      # Interactive chat session
"""

import os
import sys
import argparse
from typing import List, Dict, Any
from .system_prompt import SYSTEM_PROMPT

# Import the send_prompt function from the new module
try:
    from .openai_client import send_prompt
except ImportError:
    # When running directly, not as a module
    from openai_client import send_prompt

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.formatted_text import HTML


def main():
    """Main entry point."""
    # Validate required environment variables at startup
    missing_vars = []
    if not os.getenv("OPENAI_API_KEY"):
        missing_vars.append("OPENAI_API_KEY")
    if not os.getenv("OPENAI_MODEL"):
        missing_vars.append("OPENAI_MODEL")
    # Note: OPENAI_BASE_URL is optional for standard OpenAI, so we don't require it
    
    if missing_vars:
        print(f"Error: Missing required environment variable(s): {', '.join(missing_vars)}", file=sys.stderr)
        print("Please set these environment variables before running the CLI.", file=sys.stderr)
        sys.exit(1)
    
    parser = argparse.ArgumentParser(
        description="OpenAI CLI - Send prompts to OpenAI-compatible endpoints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  OPENAI_BASE_URL    - Base URL of the OpenAI-compatible API endpoint (optional for standard OpenAI)
  OPENAI_API_KEY     - API key for authentication  
  OPENAI_MODEL       - Model name to use for completions

Options:
  --list-tools       List all available tools and their descriptions

Examples:
  python -m janito4 "What is the capital of France?"  # Single prompt mode
  echo "Tell me a joke" | python -m janito4           # Pipe input mode
  python -m janito4                                 # Interactive chat mode
  python -m janito4 --list-tools                     # List available tools
        """
    )
    
    parser.add_argument(
        "prompt", 
        nargs="?", 
        help="The prompt to send to the AI (if not provided, starts interactive chat)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output (shows model and backend info)"
    )
    
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List all available tools and exit"
    )
    
    args = parser.parse_args()
    
    # Handle --list-tools option
    if args.list_tools:
        try:
            from .tooling.tools_registry import get_all_tool_schemas, get_all_tool_permissions
        except ImportError:
            from tooling.tools_registry import get_all_tool_schemas, get_all_tool_permissions
        
        schemas = get_all_tool_schemas()
        permissions = get_all_tool_permissions()
        
        print("Available Tools:")
        print("=" * 60)
        
        # Group tools by category based on name prefixes
        categories = {
            "File Operations": [],
            "System Operations": [],
            "Other": []
        }
        
        for schema in schemas:
            func_info = schema['function']
            name = func_info['name']
            perms = permissions.get(name, "")
            
            # Get parameter names only
            params = func_info['parameters']['properties']
            param_names = list(params.keys())
            
            tool_info = {
                'name': name,
                'permissions': perms,
                'params': param_names
            }
            
            if name.startswith(('Create', 'Delete', 'List', 'Read', 'Remove', 'Replace', 'Search')):
                categories["File Operations"].append(tool_info)
            elif name.startswith(('Get', 'Run')):
                categories["System Operations"].append(tool_info)
            else:
                categories["Other"].append(tool_info)
        
        # Display tools by category
        for category, tools_list in categories.items():
            if tools_list:
                print(f"\n{category}:")
                print("-" * 40)
                
                for tool in sorted(tools_list, key=lambda x: x['name']):
                    perms_str = f" [{tool['permissions']}]" if tool['permissions'] else ""
                    params_str = f" ({', '.join(tool['params'])})" if tool['params'] else " (no params)"
                    print(f"  {tool['name']}{perms_str}{params_str}")
        
        print(f"\nTotal: {len(schemas)} tools")
        print("\nPermission codes: r=read, w=write, x=execute")
        return
    
    # Check if stdin is not a tty (piped input)
    if args.prompt is None and not sys.stdin.isatty():
        # Read prompt from stdin
        try:
            prompt = sys.stdin.read().strip()
            if not prompt:
                print("Error: Empty prompt provided via stdin.", file=sys.stderr)
                sys.exit(1)
            args.prompt = prompt
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.", file=sys.stderr)
            sys.exit(130)
    
    # Handle chat mode (when no prompt is provided)
    if args.prompt is None:
        
        # Get model name for the prompt (already validated at startup)
        model = os.getenv("OPENAI_MODEL")
        
        print("Starting interactive chat session. Type 'exit' or 'quit' to end the session, 'restart' to clear conversation history.")
        print("Key bindings: F2 = restart conversation, F12 = Do It (auto-execute)")
        
        messages_history: List[Dict[str, Any]] = []
        restart_requested = False
        do_it_requested = False

        messages_history = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Create key bindings
        kb = KeyBindings()
        
        @kb.add('f2')
        def restart_chat(event: KeyPressEvent) -> None:
            """Handle F2 key to restart conversation."""
            nonlocal restart_requested
            restart_requested = True
            event.app.exit(result=None)  # Exit the current prompt
        
        @kb.add('f12')
        def do_it_action(event: KeyPressEvent) -> None:
            """Handle F12 key to trigger 'Do It' auto-execution."""
            nonlocal do_it_requested
            do_it_requested = True
            event.app.exit(result="Do It")  # Return special value to trigger auto-execution
        
        session = PromptSession(history=InMemoryHistory(), key_bindings=kb)
        
        try:
            while True:
                try:
                    restart_requested = False
                    do_it_requested = False
                    # Use HTML formatting to apply dark blue background to prompt
                    prompt_text = HTML(f'<style bg="#00008b">{model} # </style>')
                    user_input = session.prompt(prompt_text)
                    
                    # Check if F12 was pressed (Do It requested)
                    if do_it_requested:
                        print("\n[Keybinding F12] 'Do It' to continue existing plan...")
                        user_input = "Do It"  # Set input to trigger the action
                    
                    # Check if F2 was pressed (restart requested)
                    if restart_requested:
                        messages_history.clear()
                        print("\n[Keybinding F2] Conversation history cleared. Starting fresh conversation.")
                        continue
                    
                    if user_input.lower() in ['exit', 'quit']:
                        break
                    if user_input.lower() == 'restart':
                        messages_history.clear()
                        print("Conversation history cleared. Starting fresh conversation.")
                        continue
                    if user_input.strip():
                        response = send_prompt(user_input, verbose=args.verbose, previous_messages=messages_history)
                        # Add the user message and AI response to history
                        messages_history.append({"role": "user", "content": user_input})
                        if response:
                            messages_history.append({"role": "assistant", "content": response})
                except KeyboardInterrupt:
                    # Prompt user for confirmation to quit
                    try:
                        confirm = session.prompt("\nDo you want to quit the conversation? (y/n): ")
                        if confirm.lower().strip() in ['y', 'yes']:
                            raise EOFError()  # Use EOFError to trigger graceful exit
                        # If user says no, continue the loop
                        continue
                    except (KeyboardInterrupt, EOFError):
                        # If user presses Ctrl+C or Ctrl+D during confirmation, just exit
                        raise EOFError()
        except EOFError:
            pass  # Handle Ctrl+D gracefully
        print("\nChat session ended.")
        return
    
    # Handle single prompt mode
    prompt = args.prompt
    
    if not prompt:
        print("Error: Empty prompt provided.", file=sys.stderr)
        sys.exit(1)
    
    messages_history = [{"role": "system", "content": SYSTEM_PROMPT}]

    try:
        send_prompt(prompt, verbose=args.verbose, previous_messages=messages_history)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()