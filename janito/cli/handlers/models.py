"""Model listing CLI handler (--list-models)."""

from ...config_keys import normalize_provider
from ...config_loaders import load_model_from_config
from ...config_store import get_config_path, get_config_value
from ...general_config import load_provider_from_config
from ...provider_accessors import get_default_model_from_provider
from ...provider_registry import _registry


def _resolve_provider_source(args) -> tuple[str, str]:
    """Resolve the provider, with priority CLI > config.json > fallback."""
    cli_provider = getattr(args, "provider", None)
    if cli_provider:
        return cli_provider, "CLI argument"
    config_provider = load_provider_from_config()
    if config_provider:
        return config_provider, "config.json"
    return "openai", "fallback"


def _available_model_names(provider: str) -> list[str]:
    """Return the config-available model names for ``provider``.

    The available set is the provider's built-in ``models`` registry (its
    provider-config entry) plus any per-model config entries stored under
    ``providers.<provider>.models`` in config.json, so a custom model with
    model-scoped settings (e.g. ``--set max-output-tokens=...``) is listed
    too. This mirrors the set the shell's ``/model`` command and its
    autocompletion suggest. Sorted case-insensitively.

    Args:
        provider: The provider name (case-insensitive).

    Returns:
        The model names in their canonical casing.
    """
    names: set[str] = set()
    found = _registry.get(provider)
    if found is not None:
        names.update(found.model_names())

    # Configured per-model entries (custom models with model-scoped
    # settings in config.json).
    providers = get_config_value("providers")
    if isinstance(providers, dict):
        provider_config = providers.get(normalize_provider(provider))
        if isinstance(provider_config, dict):
            models = provider_config.get("models")
            if isinstance(models, dict):
                names.update(models.keys())

    return sorted(names, key=str.lower)


def handle_list_models(args) -> int:
    """Handle --list-models command.

    Lists every model config-available from the provider (set via
    ``--provider`` or defined in config.json): the provider's built-in
    models plus any per-model config entries.  The effective current model
    is flagged: ``--model``, then the provider's configured model
    (``<provider>.model``), then the provider's built-in default model.
    The built-in default model is marked ``(default)`` and the provider's
    configured model ``(configured)``.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success)
    """
    provider, provider_source = _resolve_provider_source(args)

    default_model = get_default_model_from_provider(provider)
    configured_model = load_model_from_config(provider)
    cli_model = getattr(args, "model", None)
    current_model = cli_model or configured_model or default_model

    names = _available_model_names(provider)

    # The effective current model is always shown, even when it is not part
    # of the built-in/config registry (e.g. a one-off --model name), so the
    # user sees what is in effect.
    if current_model and current_model not in names:
        names.append(current_model)
        names = sorted(names, key=str.lower)

    print(f"Models available from provider '{provider}' ({provider_source}):")
    if not names:
        print("  (none - set a model with: janito --set model=NAME)")
    else:
        for name in names:
            markers = []
            if default_model and name.lower() == default_model.lower():
                markers.append("default")
            if configured_model and name.lower() == configured_model.lower():
                markers.append("configured")
            if current_model and name.lower() == current_model.lower():
                markers.append("current")
            if markers:
                print(f"  {name} ({', '.join(markers)})")
            else:
                print(f"  {name}")

    print(f"Config file:  {get_config_path()}")
    return 0
