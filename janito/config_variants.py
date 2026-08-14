"""
Provider variant management.

A provider variant is a second configuration for an already-supported
provider, named ``<provider>-<word>`` (e.g. ``alibaba-tokenplan``).  It is
registered with ``janito --create-variant <name>``, which adds an empty
entry to the ``providers`` map in config.json; afterwards the variant name
can be used anywhere a provider name is accepted (``--provider``,
``--set provider=``, ``--set-api-key``).  The variant inherits the base
provider's built-in defaults (model, endpoint, API types, token limits,
reasoning, thinking) while keeping its own per-variant overrides
(``providers.<name>.*``) and its own API key in auth.json.

Extracted from :mod:`janito.general_config` so the core config module stays
focused on resolution and provider helpers.
"""

import logging

from .config_keys import normalize_provider
from .config_store import _load_config_file, _store, get_config_path, get_config_value

# Configure logger for this module
logger = logging.getLogger(__name__)


def load_variants() -> dict[str, dict]:
    """Load the registered provider variants from config.json.

    Variants are stored as entries of the ``providers`` map,
    ``{"<provider>-<word>": {...}}``: the dash in the name identifies the
    variants among the provider keys, and the entry dicts hold the per-variant
    config keys (``{}`` right after registration, reserved for future
    per-variant metadata).  The base provider is derived from the variant
    name's prefix (the part before the first ``-``).

    Returns:
        Dict mapping variant names to their config entries.
    """
    from .provider_registry import is_variant_style_name

    providers = get_config_value("providers")
    if not isinstance(providers, dict):
        return {}
    return {
        name: entry
        for name, entry in providers.items()
        if is_variant_style_name(name) and isinstance(entry, dict)
    }


def is_registered_variant(name: str) -> bool:
    """Return True when ``name`` is a registered provider variant.

    The check is case-insensitive and ignores surrounding whitespace.

    Args:
        name: The name to check.

    Returns:
        True if the name is registered in the ``providers`` config key.
    """
    normalized = normalize_provider(name)
    if not normalized:
        return False
    return normalized in load_variants()


def create_variant(name: str) -> str:
    """Register a provider variant in config.json.

    A variant is named ``<provider>-<word>``, where ``<provider>`` is a
    supported provider and ``<word>`` is a user-defined word (which may
    itself contain hyphens, e.g. ``alibaba-token-plan``).  Registration
    adds an empty ``providers`` entry to the primary config file (the dash
    in the name identifies it as a variant among the provider keys)::

        {"providers": {"alibaba-tokenplan": {}}}

    The base provider is derived from the name prefix; the variant inherits
    the base provider's built-in defaults while keeping its own per-variant
    overrides and its own API key (see the module section above).

    Args:
        name: The variant name, e.g. ``"alibaba-tokenplan"``.

    Returns:
        The canonical (lowercased, stripped) variant name.

    Raises:
        ValueError: If the name is not ``<provider>-<word>``, the provider
            prefix is unsupported, or the variant is already registered.
    """
    from .provider_data import PROVIDER_INFO
    from .provider_registry import parse_variant_name

    normalized = normalize_provider(name)
    if not normalized:
        raise ValueError(
            "A variant name is required, e.g. --create-variant alibaba-tokenplan "
            "(<provider>-<word>)."
        )

    parsed = parse_variant_name(normalized)
    if parsed is None:
        raise ValueError(
            f"Invalid provider variant '{name}'. "
            "A variant must be named <provider>-<word>, e.g. alibaba-tokenplan."
        )
    base, _ = parsed

    # The base must be a *supported provider* (a PROVIDER_INFO entry), not
    # another variant, so variants cannot be nested.
    if not any(key.lower() == base for key in PROVIDER_INFO):
        supported = ", ".join(sorted(PROVIDER_INFO.keys()))
        raise ValueError(
            f"Unknown base provider '{base}' for variant '{name}'. "
            f"Supported providers: {supported}"
        )

    if is_registered_variant(normalized):
        raise ValueError(f"Provider variant '{normalized}' already exists.")

    # Write to the primary config file only (never the merged view), the same
    # write target --set / --unset use.  The variant is registered as an
    # entry of the ``providers`` map.
    config = _load_config_file(get_config_path())
    providers = config.get("providers")
    if not isinstance(providers, dict):
        providers = {}
        config["providers"] = providers
    providers[normalized] = {}
    _store.save(config)
    logger.info(f"Created provider variant '{normalized}'")
    return normalized


def delete_variant(name: str) -> bool:
    """Delete a provider variant and its per-variant configuration.

    Removes the variant's ``providers`` entry (the registration marker plus
    every per-variant config key under ``providers.<name>.*``: model,
    endpoint and the per-model settings under ``providers.<name>.models``)
    and the variant's API key in ``auth.json``.

    Args:
        name: The variant name to delete.

    Returns:
        bool: True if the variant was registered and removed, False when the
            variant is not registered.

    Raises:
        ValueError: If ``name`` is the currently configured default provider.
    """
    from .auth_config import delete_api_key
    from .general_config import load_provider_from_config

    normalized = normalize_provider(name)
    if not normalized:
        return False

    if not is_registered_variant(normalized):
        return False

    # Guard: cannot delete the variant in use as the default provider.
    default = load_provider_from_config()
    if default and normalize_provider(default) == normalized:
        raise ValueError(
            f"Provider variant '{normalized}' is the configured default provider. "
            "Switch the default first with: janito --set provider=<name>"
        )

    # Remove the variant's providers entry (its registration marker and any
    # per-variant config keys) from the primary config file.
    config = _load_config_file(get_config_path())
    providers = config.get("providers")
    if isinstance(providers, dict) and normalized in providers:
        del providers[normalized]
        if not providers:
            del config["providers"]
        _store.save(config)

    # Remove the variant's API key from auth.json (best-effort; a missing
    # key is not an error).
    delete_api_key(normalized)

    logger.info(f"Deleted provider variant '{normalized}'")
    return True
