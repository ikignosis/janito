"""Handlers for get-type CLI commands (show_config, list_providers, models, tools)."""

import sys

from janito.cli.cli_commands.list_providers import handle_list_providers
from janito.cli.cli_commands.list_models import handle_list_models
from janito.cli.cli_commands.list_tools import handle_list_tools
from janito.cli.cli_commands.check_tools import handle_check_tools
from janito.cli.cli_commands.show_config import handle_show_config
from janito.cli.cli_commands.list_config import handle_list_config
from janito.cli.cli_commands.list_drivers import handle_list_drivers
from janito.regions.cli import handle_region_info
from janito.cli.cli_commands.list_providers_region import handle_list_providers_region
from janito.cli.cli_commands.list_plugins import handle_list_plugins
from functools import partial
from janito.provider_registry import ProviderRegistry
from janito.config import config as global_config

GETTER_KEYS = [
    "show_config",
    "list_providers",
    "list_profiles",
    "list_models",
    "list_tools",
    "list_config",
    "list_drivers",
    "region_info",
    "list_providers_region",
    "list_plugins",
    "list_plugins_available",
    "list_resources",
    "check_tools",
]


def get_current_provider():
    """Get the current provider from the global config."""
    return global_config.get("provider", "none")


def handle_getter(args, config_mgr=None):
    provider_instance = None
    if getattr(args, "list_models", False):
        provider = getattr(args, "provider", None)
        if not provider:
            import sys

            print(
                "Error: No provider selected. Please set a provider using '-p PROVIDER', '--set provider=name', or configure a provider."
            )
            sys.exit(1)
        provider_instance = ProviderRegistry().get_instance(provider)
    # Lazy import to avoid overhead unless needed
    from janito.cli.cli_commands.list_profiles import handle_list_profiles

    GETTER_DISPATCH = {
        "list_providers": partial(handle_list_providers, args),
        "list_models": partial(handle_list_models, args, provider_instance),
        "list_tools": partial(handle_list_tools, args),
        "list_profiles": partial(handle_list_profiles, args),
        "show_config": partial(handle_show_config, args),
        "list_config": partial(handle_list_config, args),
        "list_drivers": partial(handle_list_drivers, args),
        "region_info": partial(handle_region_info, args),
        "list_providers_region": partial(handle_list_providers_region, args),
        "list_plugins": partial(handle_list_plugins, args),
        "list_plugins_available": partial(handle_list_plugins, args),
        "list_resources": partial(handle_list_plugins, args),
        "check_tools": partial(handle_check_tools, args),
    }
    for arg in GETTER_KEYS:
        if getattr(args, arg, False) and arg in GETTER_DISPATCH:
            return GETTER_DISPATCH[arg]()
