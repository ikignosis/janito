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

# Import MCP config functions
from janito.mcp_config import (
    get_mcp_config_path,
    list_services,
    load_mcp_config,
    remove_service,
    save_mcp_config,
)

from .base import CmdHandler
from .registry import register_command


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

    def _handle_add_stdio(self, name: str, args: list[str]) -> None:
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
            if " " in arg or '"' in arg or "'" in arg:
                command_parts.append(f'"{arg}"')
            else:
                command_parts.append(arg)

        command = " ".join(command_parts)

        # Load current config
        config = load_mcp_config()

        # Add the service
        config["services"][name] = {"transport": "stdio", "command": command, "env": {}}

        # Save config
        save_mcp_config(config)

        print(f"[OK] MCP service '{name}' added successfully")
        print("  Transport: stdio")
        print(f"  Command:   {command}")

    def _handle_add_http(self, name: str, args: list[str]) -> None:
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
                if ":" in header_value:
                    key, value = header_value.split(":", 1)
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
        service_config = {"transport": "http", "url": url}

        if headers:
            service_config["headers"] = headers

        # Add the service
        config["services"][name] = service_config

        # Save config
        save_mcp_config(config)

        print(f"[OK] MCP service '{name}' added successfully")
        print("  Transport: http")
        print(f"  URL:       {url}")
        if headers:
            print(f"  Headers:   {len(headers)} header(s) set")

    def _handle_list(self) -> None:
        """List all configured MCP services as a rich table."""
        from rich.console import Console
        from rich.table import Table

        services = list_services()

        console = Console(markup=False)

        if not services:
            table = Table(
                title="Configured MCP Services",
                title_style="bold",
                header_style="bold cyan",
                show_header=False,
                box=None,
                pad_edge=False,
            )
            table.add_column("Key", style="green", no_wrap=True)
            table.add_column("Value", overflow="fold")
            table.add_row("Status", "No MCP services configured.")
            table.add_row(
                "Add stdio", "/mcp add <name> stdio <command> to add a stdio service"
            )
            table.add_row(
                "Add http", "/mcp add <name> http <url> to add an HTTP service"
            )
            table.add_row("Config file", str(get_mcp_config_path()))
            console.print(table)
            return

        table = Table(
            title="Configured MCP Services",
            title_style="bold",
            header_style="bold cyan",
        )
        table.add_column("Service", style="green", no_wrap=True)
        table.add_column("Transport", no_wrap=True)
        table.add_column("Details", overflow="fold")

        for name, service_config in services.items():
            transport = service_config.get("transport", "unknown")

            if transport == "stdio":
                details = f"Command: {service_config.get('command', '')}"
            elif transport == "http":
                details = f"URL: {service_config.get('url', '')}"
                headers = service_config.get("headers", {})
                if headers:
                    details += f"; {len(headers)} header(s)"
            else:
                details = json.dumps(service_config)

            table.add_row(name, transport, details)

        console.print(table)
        print(f"Config file: {get_mcp_config_path()}")

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
        """Print help information for the /mcp command as rich tables."""
        from rich.console import Console
        from rich.table import Table

        console = Console(markup=False)

        usage = Table(
            title="/mcp - MCP (Model Context Protocol) Service Manager",
            title_style="bold",
            header_style="bold cyan",
            show_header=False,
            box=None,
            pad_edge=False,
        )
        usage.add_column("Command", style="green", no_wrap=True)
        usage.add_column("Description", overflow="fold")
        usage.add_row(
            "/mcp add <name> stdio <command> [args...]",
            "Add a stdio transport service",
        )
        usage.add_row(
            "/mcp add <name> http <url> [--header KEY:VALUE]",
            "Add an HTTP transport service",
        )
        usage.add_row("/mcp list", "List all configured MCP services")
        usage.add_row("/mcp remove <name>", "Remove an MCP service")
        console.print(usage)

        transports = Table(
            title="Transports",
            title_style="bold",
            header_style="bold cyan",
            show_header=False,
            box=None,
            pad_edge=False,
        )
        transports.add_column("Transport", style="green", no_wrap=True)
        transports.add_column("Description", overflow="fold")
        transports.add_row(
            "stdio", "Local process via stdin/stdout (default for local servers)"
        )
        transports.add_row("http", "HTTP/SSE endpoint (for remote MCP servers)")
        console.print(transports)

        options = Table(
            title="Options",
            title_style="bold",
            header_style="bold cyan",
            show_header=False,
            box=None,
            pad_edge=False,
        )
        options.add_column("Option", style="green", no_wrap=True)
        options.add_column("Description", overflow="fold")
        options.add_row(
            "--header KEY:VALUE", "Add HTTP header (can be used multiple times)"
        )
        console.print(options)

        examples = Table(
            title="Examples",
            title_style="bold",
            header_style="bold cyan",
            show_header=False,
            box=None,
            pad_edge=False,
        )
        examples.add_column("Command", style="green", no_wrap=True)
        examples.add_column("Description", overflow="fold")
        examples.add_row("/mcp add myserver stdio python -m mcp.server", "")
        examples.add_row(
            '/mcp add myserver stdio "python -m mcp.server --port 5000"', ""
        )
        examples.add_row("/mcp add remote http https://api.example.com/mcp", "")
        examples.add_row(
            "/mcp add remote http https://api.example.com/mcp --header Authorization:Bearer xxx",
            "",
        )
        examples.add_row("/mcp list", "")
        examples.add_row("/mcp remove myserver", "")
        console.print(examples)

        print(f"Config file: {get_mcp_config_path()}")


# Register this handler
_handler = McpCmdHandler()
register_command(_handler)
