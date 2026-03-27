"""
/config command handler - displays current configuration.
"""

import os

from .base import CmdHandler
from .registry import register_command

# Import general configuration handling
from janito.general_config import get_active_provider, get_masked_api_key, load_context_window_size


def _print_config_info() -> None:
    """Print current configuration info (provider, base_url, masked API key, context window size)."""
    provider = get_active_provider()
    api_key = os.getenv("OPENAI_API_KEY", "")
    masked_key = get_masked_api_key(api_key)
    context_window_size = load_context_window_size()
    
    # Determine the actual base URL that will be used
    base_url = os.getenv("OPENAI_BASE_URL")
    if not base_url:
        # Try to get base URL from provider configuration
        try:
            from janito.provider_config import get_base_url_from_provider
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
    print(f"  Provider:           {provider}")
    print(f"  Base URL:           {base_url_display}")
    print(f"  API Key:            {masked_key}")
    print(f"  Context Window:     {context_window_size if context_window_size else '(not set)'}")
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
