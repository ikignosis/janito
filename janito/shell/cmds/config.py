"""
/config command handler - displays current configuration.
"""

from janito.auth_config import get_api_key

# Import general configuration handling
from janito.general_config import (
    get_active_provider,
    get_masked_api_key,
    load_endpoint_from_config,
    load_max_output_tokens,
)
from janito.provider_config import get_default_max_output_tokens_from_provider

from .base import CmdHandler
from .registry import register_command


def _print_config_info(provider: str | None = None) -> None:
    """Print current configuration info (provider, base_url, masked API key, max output tokens).

    Args:
        provider: The provider in effect for the current shell session (e.g.
            from ``--provider``). When None, falls back to the configured
            default provider.
    """
    if provider is None:
        provider = get_active_provider()
    api_key = get_api_key(provider) or ""
    masked_key = get_masked_api_key(api_key)
    max_output_tokens = load_max_output_tokens(provider)

    # Determine the actual base URL that will be used: a configured endpoint
    # override first, otherwise the provider's built-in default.
    base_url = load_endpoint_from_config(provider)
    if not base_url:
        from janito.provider_config import get_base_url_from_provider

        base_url = get_base_url_from_provider(provider)

    if base_url:
        base_url_display = base_url
    else:
        base_url_display = "(default OpenAI URL)"

    # Resolve the effective max output tokens: an explicit configuration value
    # first, otherwise the provider's built-in default from PROVIDER_INFO.
    if max_output_tokens:
        max_output_tokens_display = str(max_output_tokens)
    else:
        default_max_output_tokens = get_default_max_output_tokens_from_provider(
            provider
        )
        max_output_tokens_display = (
            f"{default_max_output_tokens} (default)"
            if default_max_output_tokens
            else "(not set)"
        )

    print()
    print("=" * 50)
    print("Configuration Info")
    print("=" * 50)
    print(f"  Provider:           {provider}")
    print(f"  Base URL:           {base_url_display}")
    print(f"  API Key:            {masked_key}")
    print(f"  Max Output Tokens:  {max_output_tokens_display}")
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
            _print_config_info(getattr(shell, "provider", None))
            return True
        return False


# Register this handler
_handler = ConfigCmdHandler()
register_command(_handler)
