"""
CLI Command: Check all registered tools for signature validation and availability
"""

import inspect
import sys
from typing import Dict, List, Tuple, Any


def _validate_tool_signature(tool_instance) -> Tuple[bool, List[str]]:
    """Validate the signature of a tool's run method."""
    errors = []

    if not hasattr(tool_instance, "run"):
        errors.append("Missing 'run' method")
        return False, errors

    try:
        sig = inspect.signature(tool_instance.run)
    except ValueError as e:
        errors.append(f"Invalid signature: {e}")
        return False, errors

    # Basic signature validation - just check if it's callable
    if not callable(getattr(tool_instance, "run")):
        errors.append("'run' method is not callable")

    return len(errors) == 0, errors


def _check_tool_availability(tool_instance) -> Tuple[bool, List[str]]:
    """Check if a tool is available for use."""
    errors = []

    # Check if tool has required attributes
    required_attrs = ["tool_name"]
    for attr in required_attrs:
        if not hasattr(tool_instance, attr):
            errors.append(f"Missing required attribute: {attr}")

    # Check description (optional for now)
    if not hasattr(tool_instance, "description"):
        pass  # Allow missing description

    # Check permissions
    if not hasattr(tool_instance, "permissions"):
        # Function-based tools use permissions from function decorators
        pass  # Allow missing permissions for function-based tools
    else:
        perms = tool_instance.permissions
        if (
            not hasattr(perms, "read")
            or not hasattr(perms, "write")
            or not hasattr(perms, "execute")
        ):
            errors.append("Invalid permissions structure")

    return len(errors) == 0, errors


def _get_tool_status_summary(
    tools: List[Any], disabled_tools: List[str]
) -> Dict[str, Any]:
    """Get a comprehensive status summary for all tools."""
    summary = {
        "total": len(tools),
        "available": 0,
        "disabled": 0,
        "invalid": 0,
        "details": [],
    }

    for tool in tools:
        tool_name = getattr(tool, "tool_name", str(tool))

        # Check if disabled
        is_disabled = tool_name in disabled_tools

        # Validate signature and availability
        sig_valid, sig_errors = _validate_tool_signature(tool)
        avail_valid, avail_errors = _check_tool_availability(tool)

        status = {
            "name": tool_name,
            "disabled": is_disabled,
            "signature_valid": sig_valid,
            "available": avail_valid,
            "signature_errors": sig_errors,
            "availability_errors": avail_errors,
        }

        summary["details"].append(status)

        if is_disabled:
            summary["disabled"] += 1
        elif not sig_valid or not avail_valid:
            summary["invalid"] += 1
        else:
            summary["available"] += 1

    return summary


def _print_check_results(console, summary: Dict[str, Any], verbose: bool = False):
    """Print the tool check results in a formatted way."""
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text

    # Overall summary
    summary_text = Text()
    summary_text.append(f"Total tools: {summary['total']}", style="cyan")
    summary_text.append(" | ")
    summary_text.append(f"Available: {summary['available']}", style="green")
    summary_text.append(" | ")
    summary_text.append(f"Disabled: {summary['disabled']}", style="yellow")
    summary_text.append(" | ")
    summary_text.append(f"Invalid: {summary['invalid']}", style="red")

    console.print(Panel(summary_text, title="Tool Check Summary", style="bold"))

    # Always show the table for check-tools
    table = Table(title="Tool Details", show_header=True, header_style="bold")
    table.add_column("Tool", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("Issues", style="red")

    for detail in summary["details"]:
        name = detail["name"]

        if detail["disabled"]:
            status = "[yellow]Disabled[/yellow]"
            issues = "-"
        elif not detail["available"] or not detail["signature_valid"]:
            status = "[red]Invalid[/red]"
            all_issues = detail["signature_errors"] + detail["availability_errors"]
            issues = "\n".join(all_issues)
        else:
            status = "[green]Available[/green]"
            issues = "-"

        table.add_row(name, status, issues)

    console.print(table)


def handle_check_tools(args=None):
    """Handle the --check-tools CLI command."""
    from janito.tools.adapters.local.adapter import LocalToolsAdapter
    import janito.tools  # Ensure all tools are registered

    # Load disabled tools from config
    from janito.tools.disabled_tools import DisabledToolsState
    from janito.config import config

    disabled_str = config.get("disabled_tools", "")
    if disabled_str:
        DisabledToolsState.set_disabled_tools(disabled_str)
    disabled_tools = DisabledToolsState.get_disabled_tools()

    # Initialize tools properly using the same approach as list_tools.py
    from janito.tools.adapters.local.adapter import LocalToolsAdapter
    from janito.tools.tool_base import ToolPermissions
    import janito.tools  # Ensure all tools are registered

    read = getattr(args, "read", False) if args else False
    write = getattr(args, "write", False) if args else False
    execute = getattr(args, "exec", False) if args else False
    if not (read or write or execute):
        read = write = execute = True
    from janito.tools.permissions import set_global_allowed_permissions

    set_global_allowed_permissions(
        ToolPermissions(read=read, write=write, execute=execute)
    )

    # Load disabled tools from config
    from janito.tools.disabled_tools import DisabledToolsState
    from janito.config import config

    disabled_str = config.get("disabled_tools", "")
    if disabled_str:
        DisabledToolsState.set_disabled_tools(disabled_str)
    disabled_tools = DisabledToolsState.get_disabled_tools()

    # Initialize tools using the same method as list_tools.py
    from janito.tools.initialize import initialize_tools

    registry = initialize_tools()

    # Get actual tool instances
    tool_instances = []
    for name, tool_info in registry._tools.items():
        if "instance" in tool_info:
            tool_instances.append(tool_info["instance"])

    if not tool_instances:
        print("No tools registered.")
        return

    from rich.console import Console

    console = Console()

    verbose = getattr(args, "verbose", False) if args else False

    summary = _get_tool_status_summary(tool_instances, disabled_tools)
    _print_check_results(console, summary, verbose=verbose)

    # Exit with error code if there are invalid tools
    if summary["invalid"] > 0:
        sys.exit(1)
