"""
/mcp command handler - manages MCP (Model Context Protocol) services.

Usage:
    /mcp add <name> stdio <command> [args...]        - Add a stdio transport service
    /mcp add <name> http <url> [--header KEY:VALUE]  - Add an HTTP transport service
    /mcp list                                       - List all MCP services
    /mcp remove <name>                              - Remove an MCP service
    /mcp                                            - Show this help message

Examples:
    /mcp add myserver stdio "python -m mcp.server --port 5000"
    /mcp add myserver stdio python -m mcp.server --port 5000
    /mcp add remote http https://api.example.com/mcp
    /mcp add remote http https://api.example.com/mcp --header Authorization:Bearer xxx
    /mcp list
    /mcp remove myserver
"""

import json
import shlex
from typing import List

from .base import CmdHandler
from .registry import register_command

# Import MCP config functions
from janito.mcp_config import (
    MCP_CONFIG_PATH,
    load_mcp_config,
    save_mcp_config,
    list_services,
    remove_service
)


class McpCmdHandler(CmdHandler):
    """Command handler for /mcp command."""
    
    @property
    def name(self) -> str:
        return "/mcp"
    
    def handle(self, shell, user_input: str) -> bool:
        """Handle the /mcp command."""
        if not user_input.lower().startswith(self.name.lower()):
            return False
        
        # Parse the command
        parts = user_input.split(None, 2)  # Split into at most 3 parts
        
        if len(parts) == 1:
            # Just /mcp - show help
            self._print_help()
            return True
        
        subcommand = parts[1].lower()
        
        if subcommand == "add":
            if len(parts) < 3:
                print("Error: /mcp add requires <name> <transport> arguments")
                print("Usage: /mcp add <name> stdio <command> [args...]")
                print("       /mcp add <name> http <url> [--header KEY:VALUE]")
                return True
            self._handle_add(parts[2])
        elif subcommand == "list":
            self._handle_list()
        elif subcommand == "remove" or subcommand == "rm" or subcommand == "delete":
            if len(parts) < 3:
                print("Error: /mcp remove requires <name> argument")
                print("Usage: /mcp remove <name>")
                return True
            self._handle_remove(parts[2])
        elif subcommand == "help":
            self._print_help()
        else:
            print(f"Unknown subcommand: {subcommand}")
            self._print_help()
        
        return True
    
    def _handle_add(self, args_str: str) -> None:
        """Add an MCP service.
        
        Args:
            args_str: The argument string after 'add' (name transport [transport-args])
        """
        # Parse arguments, handling quotes properly
        try:
            args = shlex.split(args_str)
        except ValueError as e:
            print(f"Error parsing arguments: {e}")
            return
        
        if len(args) < 2:
            print("Error: /mcp add requires <name> and <transport> arguments")
            print("Usage: /mcp add <name> stdio <command> [args...]")
            print("       /mcp add <name> http <url> [--header KEY:VALUE]")
            return
        
        name = args[0]
        transport = args[1].lower()
        
        if transport == "stdio":
            self._handle_add_stdio(name, args[2:] if len(args) > 2 else [])
        elif transport == "http":
            self._handle_add_http(name, args[2:] if len(args) > 2 else [])
        else:
            print(f"Error: Unknown transport type '{transport}'")
            print("Supported transports: stdio, http")
    
    def _handle_add_stdio(self, name: str, args: List[str]) -> None:
        """Add a stdio transport MCP service.
        
        Args:
            name: The service name
            args: Command and arguments
        """
        if not args:
            print("Error: stdio transport requires a command")
            print("Usage: /mcp add <name> stdio <command> [args...]")
            return
        
        # Build command string from args
        command_parts = []
        for arg in args:
            if ' ' in arg or '"' in arg or "'" in arg:
                command_parts.append(f'"{arg}"')
            else:
                command_parts.append(arg)
        
        command = ' '.join(command_parts)
        
        # Load current config
        config = load_mcp_config()
        
        # Add the service
        config["services"][name] = {
            "transport": "stdio",
            "command": command,
            "env": {}
        }
        
        # Save config
        save_mcp_config(config)
        
        print(f"[OK] MCP service '{name}' added successfully")
        print(f"  Transport: stdio")
        print(f"  Command:   {command}")
    
    def _handle_add_http(self, name: str, args: List[str]) -> None:
        """Add an HTTP transport MCP service.
        
        Args:
            name: The service name
            args: URL and optional headers
        """
        if not args:
            print("Error: http transport requires a URL")
            print("Usage: /mcp add <name> http <url> [--header KEY:VALUE]")
            return
        
        url = args[0]
        headers = {}
        
        # Parse --header flags
        i = 1
        while i < len(args):
            if args[i] == "--header" and i + 1 < len(args):
                header_value = args[i + 1]
                if ':' in header_value:
                    key, value = header_value.split(':', 1)
                    headers[key.strip()] = value.strip()
                else:
                    print(f"Warning: Ignoring invalid header format: {header_value}")
                    print("  Expected format: --header KEY:VALUE")
                i += 2
            else:
                print(f"Warning: Ignoring unexpected argument: {args[i]}")
                i += 1
        
        # Load current config
        config = load_mcp_config()
        
        # Build service config
        service_config = {
            "transport": "http",
            "url": url
        }
        
        if headers:
            service_config["headers"] = headers
        
        # Add the service
        config["services"][name] = service_config
        
        # Save config
        save_mcp_config(config)
        
        print(f"[OK] MCP service '{name}' added successfully")
        print(f"  Transport: http")
        print(f"  URL:       {url}")
        if headers:
            print(f"  Headers:   {len(headers)} header(s) set")
    
    def _handle_list(self) -> None:
        """List all configured MCP services."""
        services = list_services()
        
        print()
        print("=" * 60)
        print("Configured MCP Services")
        print("=" * 60)
        
        if not services:
            print("  No MCP services configured.")
            print()
            print("  Use /mcp add <name> stdio <command> to add a stdio service")
            print("  Use /mcp add <name> http <url> to add an HTTP service")
        else:
            for name, service_config in services.items():
                transport = service_config.get("transport", "unknown")
                
                print(f"  {name}")
                print(f"    Transport: {transport}")
                
                if transport == "stdio":
                    command = service_config.get("command", "")
                    print(f"    Command:   {command}")
                elif transport == "http":
                    url = service_config.get("url", "")
                    print(f"    URL:       {url}")
                    headers = service_config.get("headers", {})
                    if headers:
                        header_count = len(headers)
                        print(f"    Headers:  {header_count} header(s)")
                else:
                    print(f"    Config:   {json.dumps(service_config)}")
                print()
        
        print(f"  Config file: {MCP_CONFIG_PATH}")
        print("=" * 60)
        print()
    
    def _handle_remove(self, name: str) -> None:
        """Remove an MCP service.
        
        Args:
            name: The name of the service to remove
        """
        if remove_service(name):
            print(f"[OK] MCP service '{name}' removed successfully")
        else:
            print(f"Error: MCP service '{name}' not found")
    
    def _print_help(self) -> None:
        """Print help information for the /mcp command."""
        print()
        print("=" * 60)
        print("/mcp - MCP (Model Context Protocol) Service Manager")
        print("=" * 60)
        print()
        print("Usage:")
        print("  /mcp add <name> stdio <command> [args...]")
        print("                      Add a stdio transport service")
        print()
        print("  /mcp add <name> http <url> [--header KEY:VALUE]")
        print("                      Add an HTTP transport service")
        print()
        print("  /mcp list           List all configured MCP services")
        print()
        print("  /mcp remove <name>  Remove an MCP service")
        print()
        print("Transports:")
        print("  stdio   - Local process via stdin/stdout (default for local servers)")
        print("  http    - HTTP/SSE endpoint (for remote MCP servers)")
        print()
        print("Options:")
        print("  --header KEY:VALUE  Add HTTP header (can be used multiple times)")
        print()
        print("Examples:")
        print("  /mcp add myserver stdio python -m mcp.server")
        print('  /mcp add myserver stdio "python -m mcp.server --port 5000"')
        print()
        print("  /mcp add remote http https://api.example.com/mcp")
        print('  /mcp add remote http https://api.example.com/mcp --header Authorization:Bearer xxx')
        print()
        print("  /mcp list")
        print("  /mcp remove myserver")
        print()
        print(f"  Config file: {MCP_CONFIG_PATH}")
        print("=" * 60)
        print()


# Register this handler
_handler = McpCmdHandler()
register_command(_handler)
