"""CLI command handlers."""

from .auth import handle_set_api_key, handle_list_auth
from .config import handle_get_config, handle_set_config, handle_unset_config, handle_config_interactive
from .info import handle_info
from .tools import handle_list_tools, handle_list_mcp
from .secrets import (
    handle_set_secret,
    handle_get_secret,
    handle_delete_secret,
    handle_list_secrets,
)

__all__ = [
    "handle_set_api_key",
    "handle_list_auth",
    "handle_get_config",
    "handle_set_config",
    "handle_unset_config",
    "handle_config_interactive",
    "handle_info",
    "handle_list_tools",
    "handle_list_mcp",
    "handle_set_secret",
    "handle_get_secret",
    "handle_delete_secret",
    "handle_list_secrets",
]
