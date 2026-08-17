"""CLI command handlers."""

from .auth import handle_list_keys, handle_set_api_key
from .config import (
    handle_config_interactive,
    handle_get_config,
    handle_set_config,
    handle_unset_config,
)
from .info import handle_info, handle_show_config, handle_show_system_prompt
from .plugins import handle_install_plugin, handle_list_plugins, handle_uninstall_plugin
from .providers import handle_show_providers
from .secrets import (
    handle_delete_secret,
    handle_get_secret,
    handle_list_secrets,
    handle_set_secret,
)
from .skills import handle_install_skill, handle_list_skills, handle_uninstall_skill
from .tools import handle_list_mcp, handle_list_tools
from .variants import handle_create_variant, handle_delete_variant

__all__ = [
    "handle_config_interactive",
    "handle_create_variant",
    "handle_delete_secret",
    "handle_delete_variant",
    "handle_get_config",
    "handle_get_secret",
    "handle_info",
    "handle_install_plugin",
    "handle_install_skill",
    "handle_list_keys",
    "handle_list_mcp",
    "handle_list_plugins",
    "handle_list_secrets",
    "handle_list_skills",
    "handle_list_tools",
    "handle_set_api_key",
    "handle_set_config",
    "handle_set_secret",
    "handle_show_config",
    "handle_show_providers",
    "handle_show_system_prompt",
    "handle_uninstall_plugin",
    "handle_uninstall_skill",
    "handle_unset_config",
]
