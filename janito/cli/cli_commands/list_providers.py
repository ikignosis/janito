"""
CLI Command: List supported LLM providers
"""

from janito.provider_registry import list_providers
from janito.cli.cli_commands.ping_providers import handle_ping_providers


def handle_list_providers(args=None):
    # Check if ping flag is set
    if args and getattr(args, "ping", False):
        handle_ping_providers(args)
    else:
        list_providers()
    return
