"""
/config command handler - displays current configuration.
"""

import os
import json
from pathlib import Path

from .base import CmdHandler
from .registry import register_command


def _get_masked_api_key(api_key: str) -> str:
    """Mask an API key to show only first and last few characters."""
    if not api_key:
        return "(not set)"
    if len(api_key) <= 12:
        return "***"
    return f"{api_key[:6]}...{api_key[-4:]}"


def _load_provider_from_config():
    """Load provider name from ~/.janito/config.json if it exists."""
    config_path = Path.home() / ".janito" / "config.json"
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config.get("provider")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _get_active_provider() -> str:
    """Determine the active provider based on config and environment."""
    # 1. First check config.json for provider
    config_provider = _load_provider_from_config()
    if config_provider:
        return config_provider
    
    # 2. Check auth.json for default provider
    try:
        from janito4.auth_config import get_default_provider
    except ImportError:
        try:
            from auth_config import get_default_provider
        except ImportError:
            return "openai"
    
    default_provider = get_default_provider()
    if default_provider:
        return default_provider
    
    # 3. Fall back to 'openai'
    return "openai"


def _print_config_info() -> None:
    """Print current configuration info (provider, base_url, masked API key)."""
    provider = _get_active_provider()
    api_key = os.getenv("OPENAI_API_KEY", "")
    masked_key = _get_masked_api_key(api_key)
    
    # Determine the actual base URL that will be used
    base_url = os.getenv("OPENAI_BASE_URL")
    if not base_url:
        # Try to get base URL from provider configuration
        try:
            from janito4.provider_config import get_base_url_from_provider
        except ImportError:
            try:
                from provider_config import get_base_url_from_provider
            except ImportError:
                base_url = None
        
        if base_url:
            base_url_display = f"{base_url} (from provider: {provider})"
        else:
            base_url_display = "(default OpenAI URL)"
    else:
        base_url_display = base_url
    
    print()
    print("=" * 50)
    print("Configuration Info")
    print("=" * 50)
    print(f"  Provider:    {provider}")
    print(f"  Base URL:   {base_url_display}")
    print(f"  API Key:    {masked_key}")
    print("=" * 50)
    print()


class ConfigCmdHandler(CmdHandler):
    """Command handler for /config command."""
    
    @property
    def name(self) -> str:
        return "/config"
    
    def handle(self, shell, user_input: str) -> bool:
        """Handle the /config command."""
        if user_input.lower() == self.name.lower():
            _print_config_info()
            return True
        return False


# Register this handler
_handler = ConfigCmdHandler()
register_command(_handler)
