"""
/provider command handler - switches the active provider.

Usage:
    /provider            - Show the current provider and the available providers
    /provider <name>     - Set the active provider

The provider name is validated against the built-in providers
(``PROVIDER_INFO``) and the registered provider variants
(``janito --create-variant``), then stored as the ``provider`` value in
config.json (the same operation as ``janito --set provider=<name>``). The
switch takes effect immediately for the running session: the shell's
displayed provider (bottom toolbar) and model are updated and the send
function is rebound to the new provider (its API type re-resolved), whether
or not the session was started with ``--provider``.

Switching the provider clears the LLM conversation history (system prompt
preserved) so the previous provider's/model's context does not leak into the
new one.
"""

from collections.abc import Iterable

from .base import CmdHandler
from .registry import register_command


def available_provider_names(prefix: str = "") -> Iterable[str]:
    """Return provider names (built-in + registered variants) matching ``prefix``.

    Matching is case-insensitive and the result is sorted
    case-insensitively; with an empty prefix every available provider is
    returned.  Used both by the ``/provider`` display and by the shell's
    argument autocompletion.

    Args:
        prefix: The partial provider name typed so far.

    Returns:
        The matching provider names in their canonical casing.
    """
    from janito.provider_validation import list_supported_providers, list_variants

    names = list_supported_providers() + list_variants()
    lowered = prefix.lower()
    return sorted(
        (name for name in names if name.lower().startswith(lowered)),
        key=str.lower,
    )


class ProviderCmdHandler(CmdHandler):
    """Command handler for /provider command."""

    @property
    def name(self) -> str:
        return "/provider"

    def handle(self, shell, user_input: str) -> bool:
        """Handle the /provider command."""
        parts = user_input.strip().split(None, 1)
        if not parts or parts[0].lower() != self.name.lower():
            return False

        if len(parts) == 1:
            self._show_current(shell)
        else:
            self._switch_provider(shell, parts[1].strip())
        return True

    @staticmethod
    def _show_current(shell) -> None:
        """Print the current provider and every available provider."""
        from janito.general_config import get_active_provider

        current = getattr(shell, "provider", None) or get_active_provider()
        print(f"Current provider: {current}")
        print("Available providers:")
        for name in available_provider_names():
            print(f"  {name}")
        print("Switch with: /provider <name>")

    @staticmethod
    def _switch_provider(shell, provider_name: str) -> None:
        """Validate, persist and apply the new provider."""
        from janito.config_loaders import load_model_from_config
        from janito.config_store import get_config_path, set_config_value
        from janito.general_config import get_active_provider
        from janito.provider_accessors import get_default_model_from_provider
        from janito.provider_validation import validate_provider_name

        try:
            canonical = validate_provider_name(provider_name)
        except ValueError as e:
            print(f"Error: {e}")
            return

        # The provider in effect before the switch: the session's displayed
        # provider (set from --provider at startup, or updated by an earlier
        # /provider switch), else the configured default.  Captured before the
        # config write below so it reflects the *old* state.
        previous = getattr(shell, "provider", None) or get_active_provider()

        set_config_value("provider", canonical)
        shell.provider = canonical

        # Keep the toolbar's model display truthful: re-resolve the effective
        # model for the new provider (configured model, else built-in default).
        model = load_model_from_config(canonical) or get_default_model_from_provider(
            canonical
        )
        if model:
            shell.model = model

        print(f"[OK] Provider set to '{canonical}' (config: {get_config_path()})")

        # The switch takes effect in real time: rebind the shell's send
        # function to the new provider (its API type re-resolved), so
        # subsequent turns use the new provider even when the session was
        # started with --provider.  The conversation belongs to the provider
        # serving it: when the effective provider changes, the previous
        # model's context must not leak into the new one, so start a fresh
        # conversation (system prompt preserved).
        if (previous or "").lower() != canonical.lower():
            factory = getattr(shell, "send_factory", None)
            if factory is not None and hasattr(shell, "send_prompt_func"):
                shell.send_prompt_func = factory(canonical)
            shell.initialize_history(
                system_prompt=getattr(shell, "_system_prompt", None)
            )
            print("Conversation history cleared (provider changed).")


# Register this handler
_handler = ProviderCmdHandler()
register_command(_handler)
