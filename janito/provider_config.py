"""
Provider configuration management for Janito CLI.

Handles provider-specific settings including default models, default max
output tokens, and base URLs (endpoints) for the API.

The static provider registry (``PROVIDER_INFO``), the optional-package map
(``REQUIRES_BY_API_TYPE``) and the ``CUSTOM_ENDPOINT`` marker live in
:mod:`janito.provider_data`; they are re-exported here so existing
``janito.provider_config.<name>`` references keep working.
"""

from .provider_data import (  # noqa: F401 (re-exported for backward compat)
    CUSTOM_ENDPOINT_MARKER,
    PROVIDER_INFO,
    REQUIRES_BY_API_TYPE,
)


def get_provider_info(provider: str) -> dict | None:
    """
    Get the full ``PROVIDER_INFO`` entry for a given provider name.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The provider info dict if found, ``None`` otherwise.
    """
    if not provider:
        return None

    # Try exact match first, then case-insensitive.
    if provider in PROVIDER_INFO:
        return PROVIDER_INFO[provider]

    provider_lower = provider.lower()
    for key, value in PROVIDER_INFO.items():
        if key.lower() == provider_lower:
            return value

    return None


def get_base_url_from_provider(provider: str) -> str | None:
    """
    Get the base URL (endpoint) for a given provider name.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The base URL if found, None otherwise.
        For "custom" provider, returns the "CUSTOM_ENDPOINT" marker.
    """
    info = get_provider_info(provider)
    if info is None:
        return None
    return info.get("endpoint")


def get_endpoint_by_api_type(provider: str) -> dict[str, str] | None:
    """
    Get the per-API-type endpoint map for a given provider name.

    Each entry maps a canonical API type (``"Completions"``, ``"Responses"``,
    ``"Anthropic"``, ...) to the base URL used for that API type. When the
    dict holds a **single** entry, that URL is the default for *any* API type
    on the provider (unless a config endpoint override is set) -- see
    :func:`get_endpoint_for_api_type`.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The ``endpoint_by_api_type`` dict if the provider declares one,
        ``None`` otherwise (either the provider is unknown or it has a single
        built-in endpoint shared by all its API types).
    """
    info = get_provider_info(provider)
    if info is None:
        return None
    return info.get("endpoint_by_api_type")


def get_endpoint_for_api_type(provider: str, api_type: str | None = None) -> str | None:
    """
    Get the base URL for a provider's API type, honoring ``endpoint_by_api_type``.

    Resolution rules:

    1. If the provider declares an ``endpoint_by_api_type`` dict with a
       **single** entry, that URL is returned for *any* API type (it is the
       provider's default endpoint).
    2. Otherwise, if ``api_type`` is given and present in the dict, that
       entry's URL is returned.
    3. Otherwise the provider's single built-in ``endpoint`` is returned
       (``None`` for standard OpenAI, the ``CUSTOM_ENDPOINT`` marker for
       "custom").

    A per-provider config endpoint override (``--set endpoint=...``) always
    wins over this resolution; callers (e.g. ``resolve_runtime_config``)
    prefer ``load_endpoint_from_config`` before consulting this helper.

    Args:
        provider: The provider name (case-insensitive)
        api_type: The canonical API type (e.g. ``"Completions"``) whose
            endpoint to look up. May be ``None`` when the caller only wants
            the provider's default endpoint.

    Returns:
        The base URL for the provider/API type, or ``None`` if the provider is
        unknown or has no endpoint.
    """
    info = get_provider_info(provider)
    if info is None:
        return None

    by_type = info.get("endpoint_by_api_type")
    if by_type:
        # A single-element dict is the default endpoint for any API type.
        if len(by_type) == 1:
            return next(iter(by_type.values()))
        if api_type and api_type in by_type:
            return by_type[api_type]

    return info.get("endpoint")


def get_all_api_types() -> list[str]:
    """
    List every canonical API type the CLI understands.

    The two OpenAI-SDK types (``"Responses"`` and ``"Completions"``) plus the
    keys of :data:`REQUIRES_BY_API_TYPE` (e.g. ``"Anthropic"`` for the native
    Anthropic SDK). Used by ``normalize_api_type`` / ``--api-type`` validation
    and by the web API-type comboboxes.

    Returns:
        Sorted list of canonical API type names.
    """
    return sorted(set(("Responses", "Completions")) | set(REQUIRES_BY_API_TYPE))


def get_required_package_for_api_type(api_type: str) -> str | None:
    """
    Get the optional Python package required by an API type, if any.

    API types served by the OpenAI SDK (``"Responses"`` / ``"Completions"``)
    return ``None``: ``openai`` is a hard dependency. Native-SDK API types
    (e.g. ``"Anthropic"``) return the package that must be installed for them
    to work (see :data:`REQUIRES_BY_API_TYPE`).

    Args:
        api_type: The API type name (case-insensitive)

    Returns:
        The required package name, or ``None`` when the API type has no
        optional-package requirement (or is unknown).
    """
    if not api_type:
        return None
    api_type_lower = api_type.strip().lower()
    for key, package in REQUIRES_BY_API_TYPE.items():
        if key.lower() == api_type_lower:
            return package
    return None


def is_api_type_available(api_type: str) -> bool:
    """
    Check whether an API type's required package is installed.

    API types without an optional-package requirement (``Responses`` /
    ``Completions``) are always available.

    Args:
        api_type: The API type name (case-insensitive)

    Returns:
        ``True`` when the API type can be used (its required package is
        installed or it has no requirement), ``False`` otherwise.
    """
    package = get_required_package_for_api_type(api_type)
    if package is None:
        return True
    import importlib.util

    return importlib.util.find_spec(package) is not None


def ensure_api_type_available(api_type: str) -> None:
    """
    Abort with an actionable message when an API type's package is missing.

    Called when the user attempts to *set* an API type (``--set api-type=...``
    or the web Settings drawer). When the API type has no optional-package
    requirement, this is a no-op.

    Args:
        api_type: The canonical API type name (e.g. ``"Anthropic"``)

    Raises:
        ValueError: If the API type requires an optional package that is not
            installed. The message names the package and how to install it.
    """
    package = get_required_package_for_api_type(api_type)
    if package is None:
        return
    import importlib.util

    if importlib.util.find_spec(package) is None:
        raise ValueError(
            f"API type '{api_type}' requires the optional '{package}' package, "
            f"which is not installed. "
            f"Install it with: pip install {package}"
        )


def get_default_model_from_provider(provider: str) -> str | None:
    """
    Get the built-in default model for a given provider name.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The default model if the provider has one, ``None`` otherwise (either
        the provider is unknown or it has no default model, e.g. "custom").
    """
    info = get_provider_info(provider)
    if info is None:
        return None
    return info.get("model")


def get_default_max_output_tokens_from_provider(provider: str) -> int | None:
    """
    Get the built-in default max output tokens for a given provider name.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The default max output tokens if the provider has one, ``None``
        otherwise (either the provider is unknown or it has no default).
    """
    info = get_provider_info(provider)
    if info is None:
        return None
    return info.get("max_output_tokens")


def get_default_max_input_tokens_from_provider(provider: str) -> int | None:
    """
    Get the built-in default max input tokens for a given provider name.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The default max input tokens if the provider has one, ``None``
        otherwise (either the provider is unknown or it has no default).
    """
    info = get_provider_info(provider)
    if info is None:
        return None
    return info.get("max_input_tokens")


def get_default_reasoning_level_from_provider(provider: str) -> str | None:
    """
    Get the built-in default reasoning level for a given provider name.

    This is the reasoning level/effort used by default for the provider's
    default model when it supports configurable reasoning depth (e.g. ``xhigh``
    for Alibaba's ``qwen3.8-max``).

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The default reasoning level if the provider has one, ``None``
        otherwise (either the provider is unknown or it has no default).
    """
    info = get_provider_info(provider)
    if info is None:
        return None
    return info.get("reasoning_level")


def get_supported_reasoning_levels_from_provider(provider: str) -> list | None:
    """
    Get the supported reasoning levels for a given provider name.

    Each entry is a dict with an ``effort`` key and a human-readable
    ``description``, describing the reasoning depths the provider's default
    model supports (e.g. ``low``/``medium``/``xhigh`` for Alibaba's
    ``qwen3.8-max``).

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The list of supported reasoning levels if the provider declares them,
        ``None`` otherwise (either the provider is unknown or it has no
        configurable reasoning).
    """
    info = get_provider_info(provider)
    if info is None:
        return None
    return info.get("supported_reasoning_levels")


def get_default_thinking_from_provider(provider: str) -> bool:
    """
    Get the built-in default for thinking mode for a given provider name.

    Providers whose models reason by default (DeepSeek, Alibaba/Qwen) declare
    ``thinking: True``; everyone else falls back to ``False``. The CLI
    ``--thinking`` flag still forces thinking on explicitly.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        True if the provider's models use thinking mode by default, False
        otherwise (including unknown providers).
    """
    info = get_provider_info(provider)
    if info is None:
        return False
    return bool(info.get("thinking"))


def get_supported_api_types_from_provider(provider: str) -> list[str] | None:
    """
    Get the list of API types a given provider supports.

    Each entry declares which API types it can talk to: ``"Responses"``
    (the Responses API, ``client.responses.create``) and/or
    ``"Completions"`` (the Chat Completions API,
    ``client.chat.completions.create``).

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The list of supported API types (e.g. ``["Responses", "Completions"]``
        for OpenAI), ``None`` if the provider is unknown.
    """
    info = get_provider_info(provider)
    if info is None:
        return None
    return info.get("supported_api_types")


def get_default_api_type_from_provider(provider: str) -> str | None:
    """
    Get the built-in default API type for a given provider name.

    The default is the **first** entry of the provider's
    ``supported_api_types`` list (e.g. ``"Responses"`` for OpenAI). The
    effective API type can be overridden per-provider with
    ``--set api-type=...`` or per-call with ``--api-type``.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The default API type (``"Responses"`` or ``"Completions"``), or
        ``None`` if the provider is unknown or declares no supported types.
    """
    supported = get_supported_api_types_from_provider(provider)
    if not supported:
        return None
    return supported[0]


def get_responses_in_server_from_provider(provider: str) -> bool:
    """
    Get whether the provider's Responses API keeps conversation state server-side.

    When ``True`` (e.g. OpenAI), the Responses endpoint stores the
    conversation and turns are chained with ``previous_response_id``. When
    ``False`` (e.g. DeepSeek), the ``/responses`` endpoint is **stateless**:
    it cannot resolve a previous response id, so the client must track and
    re-send the entire conversation history on every request (like Chat
    Completions).

    A per-provider override stored in ``~/.janito/config.json`` under
    ``providers.<name>.responses-in-server`` (set from the CLI with
    ``--set responses-in-server=...`` or from the web Settings drawer's
    Advanced section) wins over the built-in default, so providers that ship
    a default can still be flipped per deployment.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        ``True`` if the provider's Responses API keeps server-side state,
        ``False`` if it is stateless. Defaults to ``True`` for providers that
        do not declare the flag (the Responses API design) and for unknown
        providers.
    """
    # A configured override takes priority over the built-in default.  The
    # import is deferred to avoid a module-level cycle (general_config does
    # not import provider_config at import time either).
    from .general_config import load_responses_in_server_from_config

    override = load_responses_in_server_from_config(provider)
    if override is not None:
        return override

    info = get_provider_info(provider)
    if info is None:
        return True
    return bool(info.get("responses_in_server", True))


def canonical_provider_name(provider: str) -> str | None:
    """
    Return the canonical (correctly cased) name for a supported provider.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The canonical provider name as used in ``PROVIDER_INFO`` if the
        provider is supported, otherwise ``None``.
    """
    if not provider:
        return None

    provider_lower = provider.strip().lower()
    if not provider_lower:
        return None

    for key in PROVIDER_INFO:
        if key.lower() == provider_lower:
            return key
    return None


def is_supported_provider(provider: str) -> bool:
    """
    Check if a provider name is a supported provider (i.e. it maps to an entry
    in :data:`PROVIDER_INFO`).

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        True if the provider is supported, False otherwise
    """
    return canonical_provider_name(provider) is not None


def is_custom_provider(provider: str) -> bool:
    """
    Check if a provider is the special "custom" provider.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        True if the provider is "custom", False otherwise
    """
    if not provider:
        return False
    return provider.lower() == "custom"


def validate_provider_name(provider: str) -> str:
    """
    Validate a provider name against the supported providers and return its
    canonical form.

    A provider is considered valid only if it maps to an entry in
    :data:`PROVIDER_INFO`.

    Args:
        provider: The provider name to validate (case-insensitive)

    Returns:
        The canonical (correctly cased) provider name.

    Raises:
        ValueError: If the provider is not supported. The message enumerates
            the supported providers.
    """
    canonical = canonical_provider_name(provider)
    if canonical is None:
        supported = ", ".join(sorted(PROVIDER_INFO.keys()))
        raise ValueError(
            f"Unknown provider '{provider}'. Supported providers: {supported}"
        )
    return canonical


def list_supported_providers() -> list:
    """
    List all supported providers.

    Returns:
        List of provider names
    """
    return list(PROVIDER_INFO.keys())
