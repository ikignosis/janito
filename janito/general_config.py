"""
General configuration module for managing ~/.janito/config.json.

This module provides a centralized interface for all config.json-related
operations.  The per-provider loaders (``load_model_from_config``,
``load_max_output_tokens``, ...) live in :mod:`janito.config_loaders` and the
CLI-facing helpers (``set_config_from_cli``, ``get_config_from_cli``,
``unset_config_key_from_cli``, ``ProviderRequiredError``) live in
:mod:`janito.config_cli`; both are re-exported here so existing
``janito.general_config.<name>`` references keep working.
"""

import json
import logging
from pathlib import Path
from typing import Any

from .auth_config import get_default_provider
from .config_dir import get_config_dir, get_config_file_paths

# Configure logger for this module
logger = logging.getLogger(__name__)


# Default config file path. Retained for backward compatibility; prefer
# :func:`get_config_path` which honors the runtime -c/--config-dir override.
CONFIG_PATH = get_config_dir() / "config.json"

# Config keys that are stored per-provider (as ``<provider>.<key>``)
PROVIDER_SCOPED_KEYS = {
    "model",
    "endpoint",
    "max-input-tokens",
    "max-output-tokens",
    "reasoning-level",
    "api-type",
    "responses-in-server",
}

# Config keys whose values should be coerced to int when set via CLI.
INT_VALUED_KEYS = {"max-input-tokens", "max-output-tokens"}

# Config keys whose values should be coerced to bool when set via CLI.
BOOL_VALUED_KEYS = {"responses-in-server"}

# Provider variants are stored as entries of the ``providers`` map: a variant
# name (``<provider>-<word>``, e.g. ``alibaba-tokenplan``) maps to a dict of
# per-variant config keys (``{}`` right after registration).  The dash in the
# name identifies the variants among the provider keys (see ``load_variants``).


def get_config_path() -> Path:
    """Get the path to the config.json file (the write target).

    Returns:
        Path: Path to <config-dir>/config.json (defaults to ~/.janito/config.json)
    """
    return get_config_dir() / "config.json"


def get_config_paths() -> list[Path]:
    """Get all config.json paths used for resolution, in priority order.

    With ``-l`` / ``--local`` the project-local path (``./.janito/config.json``)
    comes first, followed by the base path (``~/.janito/config.json`` or the
    ``-c`` / ``--config-dir`` override). Otherwise only the base path is
    returned.

    Returns:
        List of paths, highest priority first.
    """
    return get_config_file_paths("config.json")


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep-merge ``override`` into a copy of ``base`` (override wins).

    Nested dicts are merged recursively so a local ``providers`` structure
    overrides the global one per provider/subkey instead of replacing it
    wholesale.

    Args:
        base: The base mapping (e.g. the global config).
        override: The mapping applied on top (e.g. the local config).

    Returns:
        A new merged dict; neither input is mutated.
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_config_file(config_path: Path) -> dict[str, Any]:
    """Load a single config.json file.

    Args:
        config_path: Path to the config file to read.

    Returns:
        The parsed config, or an empty dict when the file is missing or invalid.
    """
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        return {}


class ConfigStore:
    """Read/write primitives for ``~/.janito/config.json``.

    The store centralizes the four config operations (``load``, ``save``,
    ``get``, ``set``/``unset``) plus the provider-scoped key handling that
    ``set`` and ``unset`` used to duplicate.  Reads merge the resolution
    chain (project-local over base when ``-l`` / ``--local`` is active);
    writes always target the primary (write) config file only, never the
    merged view.
    """

    def load(self) -> dict[str, Any]:
        """Load the entire config, merged across the resolution chain.

        With ``-l`` / ``--local`` the project-local config.json (``./.janito``)
        is deep-merged over the base one (``~/.janito`` or the ``-c`` override)
        so local values take precedence; otherwise the single base file is read.

        Returns:
            Dict containing the config, or empty dict if no file exists or is invalid
        """
        paths = get_config_paths()
        if not any(path.exists() for path in paths):
            logger.debug("Config file not found")
            return {}

        merged: dict[str, Any] = {}
        # Iterate base -> local so that local entries override global ones.
        for config_path in reversed(paths):
            if not config_path.exists():
                continue
            with open(config_path, "r") as f:
                data = json.load(f)
            logger.debug(f"Loaded config from {config_path}: {list(data.keys())}")
            merged = _deep_merge(merged, data)
        return merged

    def save(self, config: dict[str, Any]) -> None:
        """Save the config dictionary to config.json.

        Args:
            config: Dictionary to save to config.json

        Raises:
            IOError: If unable to write to the config file
        """
        config_path = get_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        logger.debug(f"Saved config to {config_path}")

    def get(self, key: str) -> Any | None:
        """Get a config value by key.

        Supports both flat keys and provider-scoped keys in the nested
        structure.  For provider-scoped keys (e.g., ``"openai.model"``), it
        reads from the nested providers structure.

        Args:
            key: The config key to retrieve

        Returns:
            The config value, or None if not found or config file doesn't exist
        """
        config = self.load()

        # Check if this is a provider-scoped key (e.g., "openai.model")
        if "." in key:
            parts = key.split(".", 1)
            if len(parts) == 2:
                provider, subkey = parts
                providers = config.get("providers", {})
                if isinstance(providers, dict) and provider in providers:
                    provider_config = providers[provider]
                    if isinstance(provider_config, dict):
                        value = provider_config.get(subkey)
                        logger.debug(
                            f"Getting config '{key}': {value if value is None else '(set)'}"
                        )
                        return value

        # Fall back to flat key lookup
        value = config.get(key)
        logger.debug(f"Getting config '{key}': {value if value is None else '(set)'}")
        return value

    def set(self, key: str, value: Any) -> None:
        """Set a config value.

        Supports both flat keys and provider-scoped keys in the nested
        structure.  For provider-scoped keys (e.g., ``"openai.model"``), it
        writes to the nested providers structure.

        Args:
            key: The config key to set
            value: The value to set
        """
        logger.debug(f"Setting config '{key}' = {value}")
        # Writes target the primary config file only (never the merged view),
        # so a --set in -l/--local mode stores the value in ./.janito without
        # copying the global entries into the local file.
        config = _load_config_file(get_config_path())

        # Check if this is a provider-scoped key (e.g., "openai.model")
        if "." in key:
            parts = key.split(".", 1)
            if len(parts) == 2:
                provider, subkey = parts
                if subkey in PROVIDER_SCOPED_KEYS:
                    # Write to nested providers structure
                    providers = config.get("providers")
                    if not isinstance(providers, dict):
                        providers = {}
                        config["providers"] = providers
                    provider_config = providers.get(provider)
                    if not isinstance(provider_config, dict):
                        provider_config = {}
                        providers[provider] = provider_config
                    provider_config[subkey] = value
                    self.save(config)
                    return

        # Fall back to flat key storage
        config[key] = value
        self.save(config)

    def unset(self, key: str) -> bool:
        """Remove a config value by key.

        Supports both flat keys and provider-scoped keys in the nested
        structure.  For provider-scoped keys (e.g., ``"openai.model"``), it
        removes from the nested providers structure.  When a non-variant
        provider dict becomes empty after removal, the provider entry itself
        is also removed; an emptied variant entry is kept (``{}``) because it
        is the variant's registration marker.

        Args:
            key: The config key to remove

        Returns:
            bool: True if the key was removed, False if it didn't exist
        """
        # Writes target the primary config file only (see set).
        config = _load_config_file(get_config_path())

        # Provider-scoped keys (e.g., "openai.model") live in the nested
        # providers structure.
        if "." in key:
            parts = key.split(".", 1)
            if len(parts) == 2:
                provider, subkey = parts
                if subkey in PROVIDER_SCOPED_KEYS:
                    return self._unset_provider_scoped(config, provider, subkey)

        # Fall back to flat key removal
        if key in config:
            del config[key]
            self.save(config)
            logger.info(f"Removed config key: {key}")
            return True
        logger.debug(f"Config key not found for removal: {key}")
        return False

    def _unset_provider_scoped(
        self, config: dict[str, Any], provider: str, subkey: str
    ) -> bool:
        """Remove a provider-scoped key from the nested providers map.

        When the provider's dict becomes empty, non-variant providers are
        pruned entirely; an emptied variant entry is kept as ``{}`` because
        that dict is the variant's registration marker (see ``load_variants``).

        Args:
            config: The primary config dict (mutated in place).
            provider: The provider (or variant) name.
            subkey: A provider-scoped config key (e.g. ``model``).

        Returns:
            bool: True if the key was removed, False if it didn't exist.
        """
        providers = config.get("providers")
        if not isinstance(providers, dict):
            logger.debug(f"Config key not found for removal: {provider}.{subkey}")
            return False
        provider_config = providers.get(provider)
        if not isinstance(provider_config, dict):
            logger.debug(f"Config key not found for removal: {provider}.{subkey}")
            return False
        if subkey not in provider_config:
            logger.debug(f"Config key not found for removal: {provider}.{subkey}")
            return False
        del provider_config[subkey]
        # A variant's registration marker lives in the providers map itself,
        # so an emptied variant entry is kept as {} (only non-variant
        # providers are pruned when empty).
        if not provider_config:
            from .provider_config import is_variant_style_name

            if not is_variant_style_name(provider):
                del providers[provider]
        if not providers:
            del config["providers"]
        self.save(config)
        logger.info(f"Removed config key: {provider}.{subkey}")
        return True


# Module-level singleton store backing the functions below.
_store = ConfigStore()


def load_config() -> dict[str, Any]:
    """Load the entire config.json file (merged across the resolution chain).

    With ``-l`` / ``--local`` the project-local config.json (``./.janito``) is
    deep-merged over the base one (``~/.janito`` or the ``-c`` override) so
    local values take precedence; otherwise the single base file is read.

    Returns:
        Dict containing the config, or empty dict if no file exists or is invalid
    """
    return _store.load()


def save_config(config: dict[str, Any]) -> None:
    """Save the config dictionary to config.json.

    Args:
        config: Dictionary to save to config.json

    Raises:
        IOError: If unable to write to the config file
    """
    _store.save(config)


def get_config_value(key: str) -> Any | None:
    """Get a config value by key.

    Supports both flat keys and provider-scoped keys in the nested structure.
    For provider-scoped keys (e.g., "openai.model"), it reads from the nested
    providers structure.

    Args:
        key: The config key to retrieve

    Returns:
        The config value, or None if not found or config file doesn't exist
    """
    return _store.get(key)


def set_config_value(key: str, value: Any) -> None:
    """Set a config value.

    Supports both flat keys and provider-scoped keys in the nested structure.
    For provider-scoped keys (e.g., "openai.model"), it writes to the nested
    providers structure.

    Args:
        key: The config key to set
        value: The value to set
    """
    _store.set(key, value)


def unset_config_value(key: str) -> bool:
    """Remove a config value by key.

    Supports both flat keys and provider-scoped keys in the nested structure.
    For provider-scoped keys (e.g., "openai.model"), it removes from the nested
    providers structure.  If the provider dict becomes empty after removal, the
    provider entry itself is also removed.

    Args:
        key: The config key to remove

    Returns:
        bool: True if the key was removed, False if it didn't exist
    """
    return _store.unset(key)


# ---------------------------------------------------------------------------
# Provider variants
#
# A provider variant is a second configuration for an already-supported
# provider, named ``<provider>-<word>`` (e.g. ``alibaba-tokenplan``).  It is
# registered with ``janito --create-variant <name>``, which adds an empty
# entry to the ``providers`` map in config.json; afterwards the variant name
# can be used
# anywhere a provider name is accepted (``--provider``, ``--set provider=``,
# ``--set-api-key``).  The variant inherits the base provider's built-in
# defaults (model, endpoint, API types, token limits, reasoning, thinking)
# while keeping its own per-variant overrides (``providers.<name>.<key>``)
# and its own API key in auth.json.
# ---------------------------------------------------------------------------


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
    from .provider_config import is_variant_style_name

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
    from .provider_config import PROVIDER_INFO, parse_variant_name

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
    every provider-scoped config key under ``providers.<name>.*``: model,
    endpoint, api-type, max-input-tokens, max-output-tokens, reasoning-level,
    responses-in-server) and the variant's API key in ``auth.json``.

    Args:
        name: The variant name to delete.

    Returns:
        bool: True if the variant was registered and removed, False when the
            variant is not registered.

    Raises:
        ValueError: If ``name`` is the currently configured default provider.
    """
    from .auth_config import delete_api_key

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


def load_provider_from_config() -> str | None:
    """Load provider name from ~/.janito/config.json if it exists.

    Returns:
        str: Provider name from config, or None if not found
    """
    return get_config_value("provider")


def normalize_provider(provider: str | None) -> str | None:
    """Normalize a provider name for use as a config key prefix.

    Args:
        provider: The raw provider name (may be None)

    Returns:
        The lowercased/stripped provider name, or None if empty/None
    """
    if not provider:
        return None
    normalized = provider.strip().lower()
    return normalized or None


def determine_provider(cli_provider: str | None = None) -> str | None:
    """Determine the provider used for provider-scoped config (e.g. model).

    Unlike :func:`get_active_provider`, this does *not* fall back to a default
    provider. It is used for operations (such as ``--set model``) where a
    provider must be explicitly known.

    Priority:
    1. ``--provider`` CLI argument
    2. ``provider`` value from config.json

    Args:
        cli_provider: Provider passed via ``--provider`` (may be None)

    Returns:
        The normalized provider name, or None if it cannot be determined
    """
    provider = normalize_provider(cli_provider)
    if provider:
        return provider
    return normalize_provider(load_provider_from_config())


def model_config_key(provider: str) -> str:
    """Return the config key used to store the model for a given provider.

    Models are stored per-provider using the ``<provider>.model`` key so that
    each provider can have its own default model.

    Args:
        provider: The provider name

    Returns:
        The provider-scoped config key, e.g. ``"openai.model"``
    """
    return f"{normalize_provider(provider)}.model"


def endpoint_config_key(provider: str) -> str:
    """Return the config key used to store the endpoint for a given provider.

    Endpoints are stored per-provider using the ``<provider>.endpoint`` key so
    that each provider can have its own endpoint override.

    Args:
        provider: The provider name

    Returns:
        The provider-scoped config key, e.g. ``"custom.endpoint"``
    """
    return f"{normalize_provider(provider)}.endpoint"


def max_input_tokens_config_key(provider: str) -> str:
    """Return the config key used to store max input tokens for a provider.

    Max input tokens (the context-window limit) are stored per-provider using
    the ``<provider>.max-input-tokens`` key so that each provider can have its
    own override of the built-in default.

    Args:
        provider: The provider name

    Returns:
        The provider-scoped config key, e.g. ``"openai.max-input-tokens"``
    """
    return f"{normalize_provider(provider)}.max-input-tokens"


def reasoning_level_config_key(provider: str) -> str:
    """Return the config key used to store the reasoning level for a provider.

    Reasoning levels are stored per-provider using the
    ``<provider>.reasoning-level`` key so that each provider can have its own
    reasoning depth (e.g. ``low``/``medium``/``xhigh`` for Qwen3.8-Max).

    Args:
        provider: The provider name

    Returns:
        The provider-scoped config key, e.g. ``"alibaba.reasoning-level"``
    """
    return f"{normalize_provider(provider)}.reasoning-level"


def api_type_config_key(provider: str) -> str:
    """Return the config key used to store the API type for a provider.

    API types are stored per-provider using the ``<provider>.api-type`` key
    (``"Responses"`` or ``"Completions"``) so that each provider can select
    which API it talks to.

    Args:
        provider: The provider name

    Returns:
        The provider-scoped config key, e.g. ``"openai.api-type"``
    """
    return f"{normalize_provider(provider)}.api-type"


def normalize_api_type(value: str) -> str:
    """Normalize an API type value to its canonical form.

    Accepts ``responses``/``completions`` (and any native-SDK API type, e.g.
    ``anthropic``, ``dashscope``) in any casing -- the values used with
    ``--set api-type=...`` -- and returns the canonical form
    (``"Responses"`` / ``"Completions"`` / ``"Anthropic"`` / ``"DashScope"``,
    ...). The accepted set is the OpenAI-SDK types plus the keys of
    ``REQUIRES_BY_API_TYPE`` (see ``provider_config.get_all_api_types``).

    Args:
        value: The raw API type value

    Returns:
        The canonical API type (e.g. ``"Responses"``, ``"Completions"``,
        ``"Anthropic"`` or ``"DashScope"``).

    Raises:
        ValueError: If the value is not a known API type
    """
    from .provider_config import get_all_api_types

    known = get_all_api_types()
    raw = str(value).strip()
    for api_type in known:
        if api_type.lower() == raw.lower():
            return api_type
    raise ValueError(
        f"Unsupported API type '{value}'. Supported values: " f"{', '.join(known)}"
    )


def responses_in_server_config_key(provider: str) -> str:
    """Return the config key used to store the Responses-in-server flag.

    The flag is stored per-provider using the ``<provider>.responses-in-server``
    key (``True``/``False``) so that each provider can override whether its
    Responses API endpoint keeps the conversation state server-side (chaining
    turns with ``previous_response_id``) or is stateless (the client re-sends
    the full history on every request).

    Args:
        provider: The provider name

    Returns:
        The provider-scoped config key, e.g. ``"openai.responses-in-server"``
    """
    return f"{normalize_provider(provider)}.responses-in-server"


def get_masked_api_key(api_key: str) -> str:
    """Mask an API key, preserving its length for display.

    The returned string has the same length as ``api_key``: the first few and
    last few characters are shown and the middle is filled with ``.`` so the
    output never reveals the full key.

    Args:
        api_key: The API key to mask

    Returns:
        str: Masked API key with the same length as the input, or
            ``(not set)`` when the key is empty.
    """
    if not api_key:
        return "(not set)"
    prefix_len = 6
    suffix_len = 4
    n = len(api_key)
    middle = n - prefix_len - suffix_len
    if middle <= 0:
        # Key too short to keep both ends while preserving length; mask it all.
        return "." * n
    return f"{api_key[:prefix_len]}{'.' * middle}{api_key[-suffix_len:]}"


def get_active_provider() -> str:
    """Determine the active provider based on config.

    Priority:
    1. Provider from config.json
    2. Default provider from auth.json
    3. Fallback to 'openai'

    Returns:
        str: The active provider name
    """
    # 1. Check config.json for provider
    config_provider = load_provider_from_config()
    if config_provider:
        logger.debug(f"Active provider from config: {config_provider}")
        return config_provider

    # 3. Check auth.json for default provider
    default_provider = get_default_provider()
    if default_provider:
        logger.debug(f"Active provider from auth defaults: {default_provider}")
        return default_provider

    # 4. Fall back to 'openai'
    logger.debug("No provider found, using fallback: openai")
    return "openai"


def resolve_api_type(
    cli_api_type: str | None = None, cli_provider: str | None = None
) -> str:
    """Resolve the effective API type ("Responses" or "Completions").

    The API type selects which client the CLI talks to: the Responses API
    (``client.responses.create``, server-side conversation state) or the Chat
    Completions API (``client.chat.completions.create``, client-side history).

    Resolution rules:
      - api_type: ``--api-type`` CLI arg, then the provider's configured
        value (``--set api-type=...``), and finally the provider's built-in
        default from ``PROVIDER_INFO.supported_api_types`` (its **first**
        entry, e.g. ``"Responses"`` for OpenAI).
      - provider: ``--provider`` (``cli_provider``), then the configured
        provider (config.json), then auth.json's default, then ``"openai"``.

    Args:
        cli_api_type: API type passed via ``--api-type`` (highest priority).
            May be None.
        cli_provider: Provider passed via ``--provider``. May be None.

    Returns:
        The canonical API type: ``"Responses"`` or ``"Completions"``.

    Raises:
        ValueError: If an explicitly configured API type is neither
            ``"Responses"`` nor ``"Completions"``.
    """
    from .provider_config import get_default_api_type_from_provider

    raw = cli_api_type or load_api_type(cli_provider)
    if raw:
        try:
            return normalize_api_type(raw)
        except ValueError:
            logger.error(f"Unsupported API type: {raw}")
            raise

    provider = cli_provider or get_active_provider()
    default = get_default_api_type_from_provider(provider)
    return default or "Completions"


# ---------------------------------------------------------------------------
# Re-exports: the per-provider loaders and the CLI-facing helpers were split
# into janito.config_loaders and janito.config_cli.  Re-exporting keeps
# ``from janito.general_config import load_model_from_config, ...`` (used by
# the client modules, web backend, shell commands and tests) working.
# ---------------------------------------------------------------------------

from .config_cli import (  # noqa: E402,F401 (re-exported for backward compat)
    ProviderRequiredError,
    _coerce_bool_value,
    _coerce_int_value,
    _resolve_provider_scoped_key,
    get_config_from_cli,
    set_config_from_cli,
    unset_config_key_from_cli,
)
from .config_loaders import (  # noqa: E402,F401 (re-exported for backward compat)
    load_api_type,
    load_endpoint_from_config,
    load_max_input_tokens,
    load_max_output_tokens,
    load_model_from_config,
    load_reasoning_level,
    load_responses_in_server_from_config,
)
