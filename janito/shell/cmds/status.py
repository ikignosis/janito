"""
/status command handler - displays current configuration.
"""

from janito.auth_config import get_api_key

# Import general configuration handling
from janito.config_keys import get_masked_api_key
from janito.config_loaders import (
    load_endpoint_from_config,
    load_max_output_tokens,
    load_model_from_config,
    load_reasoning_level,
)
from janito.general_config import get_active_provider, resolve_api_type
from janito.provider_accessors import (
    get_default_max_output_tokens_from_provider,
    get_default_model_from_provider,
    get_default_reasoning_level_from_provider,
    get_default_thinking_from_provider,
    get_responses_in_server_from_provider,
)

from .base import CmdHandler
from .registry import register_command


def _print_config_info(provider: str | None = None, thinking: bool = False) -> None:
    """Print current configuration info (provider, base_url, masked API key, max output tokens).

    Model-level settings (max output tokens, reasoning level, thinking,
    Responses-in-server) are resolved for the *effective model*: the
    provider's configured model, else its built-in default model.

    Args:
        provider: The provider in effect for the current shell session (e.g.
            from ``--provider``). When None, falls back to the configured
            default provider.
        thinking: The ``--thinking`` CLI flag for the session. The effective
            thinking mode also considers the effective model's built-in
            default (True for DeepSeek and Alibaba/Qwen).
    """
    if provider is None:
        provider = get_active_provider()
    api_key = get_api_key(provider) or ""
    masked_key = get_masked_api_key(api_key)

    # Effective model for the provider: the configured model, else the
    # provider's built-in default model (None e.g. for "custom").
    model = load_model_from_config(provider) or get_default_model_from_provider(
        provider
    )

    max_output_tokens = load_max_output_tokens(provider, model)

    # Resolve the effective API type first (--set api-type, otherwise the
    # effective model's built-in default -- the first entry of its
    # supported_api_types list) so the built-in base URL can be resolved per
    # API type (endpoint_by_api_type, e.g. Anthropic's native-SDK URL).
    api_type = resolve_api_type(None, provider, model)

    # Determine the actual base URL that will be used: a configured endpoint
    # override first, otherwise the provider's built-in default for the
    # effective API type.
    base_url = load_endpoint_from_config(provider)
    if not base_url:
        from janito.provider_accessors import get_endpoint_for_api_type

        base_url = get_endpoint_for_api_type(provider, api_type)

    if base_url:
        base_url_display = base_url
    else:
        base_url_display = "(default OpenAI URL)"

    # Resolve the effective max output tokens: an explicit configuration
    # value first, otherwise the effective model's built-in default from
    # PROVIDER_INFO.
    if max_output_tokens:
        max_output_tokens_display = str(max_output_tokens)
    else:
        default_max_output_tokens = get_default_max_output_tokens_from_provider(
            provider, model
        )
        max_output_tokens_display = (
            f"{default_max_output_tokens} (default)"
            if default_max_output_tokens
            else "(not set)"
        )

    # Resolve the effective reasoning level: an explicit configuration value
    # first, otherwise the effective model's built-in default from
    # PROVIDER_INFO.
    reasoning_level = load_reasoning_level(provider, model)
    if reasoning_level:
        reasoning_level_display = reasoning_level
    else:
        default_reasoning_level = get_default_reasoning_level_from_provider(
            provider, model
        )
        reasoning_level_display = (
            f"{default_reasoning_level} (default)"
            if default_reasoning_level
            else "(not set)"
        )

    # Resolve the effective thinking mode: the --thinking flag first,
    # otherwise the effective model's built-in default from PROVIDER_INFO.
    effective_thinking = thinking or get_default_thinking_from_provider(provider, model)
    thinking_display = "enabled" if effective_thinking else "disabled"
    if effective_thinking and not thinking:
        thinking_display += " (model default)"

    # When the effective API type is the Responses API, surface whether the
    # model keeps the conversation state server-side (chained with
    # previous_response_id) or serves a stateless /responses endpoint (the
    # client re-sends the full history on every request, e.g. DeepSeek).
    responses_in_server_display = ""
    if api_type == "Responses":
        if get_responses_in_server_from_provider(provider, model):
            responses_in_server_display = "server-side (previous_response_id)"
        else:
            responses_in_server_display = "stateless (client re-sends history)"

    from rich.console import Console
    from rich.table import Table

    table = Table(
        title="Configuration Info",
        title_style="bold",
        header_style="bold cyan",
        show_header=False,
        box=None,
        pad_edge=False,
    )
    table.add_column("Key", style="green", no_wrap=True)
    table.add_column("Value", overflow="fold")
    table.add_row("Provider", provider)
    table.add_row("API Type", api_type)
    if responses_in_server_display:
        table.add_row("Responses In Server", responses_in_server_display)
    table.add_row("Base URL", base_url_display)
    table.add_row("API Key", masked_key)
    table.add_row("Max Output Tokens", max_output_tokens_display)
    table.add_row("Reasoning Level", reasoning_level_display)
    table.add_row("Thinking", thinking_display)
    Console(markup=False).print(table)


class StatusCmdHandler(CmdHandler):
    """Command handler for /status command."""

    @property
    def name(self) -> str:
        return "/status"

    def handle(self, shell, user_input: str) -> bool:
        """Handle the /status command."""
        if user_input.lower() == self.name.lower():
            _print_config_info(
                getattr(shell, "provider", None),
                getattr(shell, "thinking", False),
            )
            return True
        return False


# Register this handler
_handler = StatusCmdHandler()
register_command(_handler)
