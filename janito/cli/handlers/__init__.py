"""CLI command handlers."""

from .auth import handle_set_api_key, handle_list_auth
from .config import handle_get_config, handle_set_config, handle_unset_config, handle_config_interactive
from .info import handle_info, handle_show_config
from .tools import handle_list_tools, handle_list_mcp
from .secrets import (
    handle_set_secret,
    handle_get_secret,
    handle_delete_secret,
    handle_list_secrets,
)
from .skills import (
    handle_install_skill,
    handle_list_skills,
    handle_uninstall_skill,
)

__all__ = [
    "handle_set_api_key",
    "handle_list_auth",
    "handle_get_config",
    "handle_set_config",
    "handle_unset_config",
    "handle_config_interactive",
    "handle_info",
    "handle_show_config",
    "handle_list_tools",
    "handle_list_mcp",
    "handle_set_secret",
    "handle_get_secret",
    "handle_delete_secret",
    "handle_list_secrets",
    "handle_install_skill",
    "handle_list_skills",
    "handle_uninstall_skill",
]
