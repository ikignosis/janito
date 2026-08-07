"""
Provider configuration management for Janito CLI.

Handles provider-specific settings including default models, default max
output tokens, and base URLs (endpoints) for the API.

Provider Info:
{
    "openai": {
        "model": "gpt-4",
        "max_input_tokens": 128000,
        "max_output_tokens": 128000,
        "endpoint": None,  # Standard OpenAI - no base_url needed
    },
    # ... more providers
}
"""

# Marker for the special "custom" provider: its endpoint is not built in and
# must be supplied via config (--set endpoint).
CUSTOM_ENDPOINT_MARKER = "CUSTOM_ENDPOINT"


# Per-provider built-in defaults.
#
# Each entry describes a supported provider and carries more information than
# just the endpoint (the old ``PROVIDER_BASE_URLS`` only mapped a provider to
# its base URL). The fields are:
#
#   - "model": the model used when the user has not configured one.
#     ``None`` means the provider has no sensible default and the user must
#     set a model explicitly (e.g. the "custom" provider).
#   - "supported_api_types": the API types the provider supports
#     ("Responses" and/or "Completions"). The **first** entry is the built-in
#     default API type for the provider (e.g. OpenAI defaults to the
#     Responses API). The effective type can be overridden per-provider with
#     ``--set api-type=...`` or per-call with ``--api-type``.
#   - "responses_in_server": whether the provider's Responses API endpoint
#     keeps the conversation state server-side (so turns can be chained with
#     ``previous_response_id``). ``True`` for providers that follow the
#     OpenAI Responses API design (e.g. OpenAI); ``False`` for providers
#     whose ``/responses`` endpoint is **stateless** (e.g. DeepSeek), which
#     cannot resolve a previous response id and require the client to track
#     and re-send the entire conversation history on every request (like
#     Chat Completions). Absent defaults to ``True`` (the Responses API
#     design). Only meaningful when the provider also supports "Responses".
#   - "max_input_tokens": the maximum input-token (context window)
#     limit used as the built-in default. ``None`` means there is no built-in
#     limit (the caller falls back to its own default).
#   - "max_output_tokens": the maximum output-token limit (max_tokens
#     / max_completion_tokens) used when the user has not configured one.
#     ``None`` means there is no built-in limit (the caller falls back to its
#     own default).
#   - "reasoning_level": the reasoning level/effort used by default for
#     the provider's default model when it supports configurable reasoning
#     depth. ``None`` (or absent) means there is no built-in default.
#   - "supported_reasoning_levels": the list of reasoning levels supported by
#     the provider's default model, each with an ``effort`` key and a
#     human-readable ``description``. Absent when the model has no
#     configurable reasoning.
#   - "thinking": whether thinking mode (``extra_body=
#     {'enable_thinking': True}``) is enabled by default for the provider's
#     models. ``True`` for providers whose models reason by default (DeepSeek,
#     Alibaba/Qwen); absent (or ``False``) for the rest. The CLI ``--thinking``
#     flag still forces it on explicitly.
#   - "endpoint": the OpenAI-compatible base URL. ``None`` means the standard
#     OpenAI API endpoint (no custom base URL needed); the special
#     ``CUSTOM_ENDPOINT`` marker means the endpoint must come from config.
PROVIDER_INFO: dict[str, dict] = {
    # AI Providers with OpenAI-compatible APIs
    "openai": {
        "model": "gpt-5.6-luna",
        "supported_api_types": ["Responses", "Completions"],  # Responses is the default
        "responses_in_server": True,  # server-side conversation state (previous_response_id)
        "max_input_tokens": 1050000,
        "max_output_tokens": 128000,
        "endpoint": None,  # Standard OpenAI - no base_url needed
    },
    "minimax": {
        "model": "MiniMax-M3",
        "supported_api_types": ["Completions"],
        "max_input_tokens": 128000,
        "max_output_tokens": 511000,  # 512k
        "endpoint": "https://api.minimax.io/v1",
    },
    "xiaomi": {
        "model": "mimo-v2.5",
        "supported_api_types": ["Completions"],
        "max_input_tokens": 128000,
        "max_output_tokens": 120000,  # 128k
        "endpoint": "https://api.xiaomimimo.com/v1",
    },
    "moonshot": {
        "model": "kimi-k3-256k",
        "supported_api_types": ["Completions"],
        "max_input_tokens": 128000,
        "max_output_tokens": 250000,  # 256k
        "endpoint": "https://api.moonshot.ai/v1",
    },
    "alibaba": {
        "model": "qwen3.8-max",
        # Completions is the built-in default: DashScope's /responses endpoint
        # does not (yet) support qwen3.8-max (it rejects it with "Unsupported
        # model: 'qwen3.8-max'."), so the out-of-the-box provider must use the
        # Completions API where the default model works. The Responses API is
        # still supported for models that expose it (e.g. qwen3.7-max,
        # qwen3.6-plus, qwen3.5-plus, qwen-plus, qwen-flash) and can be
        # selected with --set api-type=Responses or --api-type responses. The
        # native DashScope SDK API type is selectable with
        # --set api-type=DashScope or --api-type DashScope (it requires the
        # optional `dashscope` package; see REQUIRES_BY_API_TYPE).
        "supported_api_types": ["Completions", "Responses", "DashScope"],
        "max_input_tokens": 1000000,  # 1M
        "max_output_tokens": 131072,
        "reasoning_level": "xhigh",
        "thinking": True,  # Qwen models reason by default
        "supported_reasoning_levels": [
            {
                "effort": "low",
                "description": "Fast responses with lighter reasoning",
            },
            {
                "effort": "medium",
                "description": "Greater reasoning depth for complex problems",
            },
            {
                "effort": "xhigh",
                "description": "Extra high reasoning depth for complex problems",
            },
        ],
        "endpoint": "https://dashscope-intl.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1",
        # Per-API-type endpoints: the OpenAI-compatible Chat Completions /
        # Responses URL and the native DashScope SDK base URL (the SDK talks
        # to the DashScope native API, not the compatible-mode gateway).
        "endpoint_by_api_type": {
            "Completions": "https://dashscope-intl.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1",
            "Responses": "https://dashscope-intl.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1",
            "DashScope": "https://dashscope-intl.aliyuncs.com/api/v1",
        },
    },
    "zai": {
        "model": "glm-5.2",
        "supported_api_types": ["Completions"],
        "max_input_tokens": 128000,
        "max_output_tokens": 1000000,  # 1M
        "endpoint": "https://api.z.ai/api/paas/v4/",
    },
    "deepseek": {
        "model": "deepseek-v4-flash",
        "supported_api_types": ["Responses", "Completions"],
        # DeepSeek's /responses endpoint is stateless: it cannot resolve a
        # previous_response_id, so the client must re-send the full history.
        "responses_in_server": False,
        "max_input_tokens": 1048576,  # 1M
        "max_output_tokens": 393216,  # 384k
        "thinking": True,  # DeepSeek models reason by default
        "endpoint": "https://api.deepseek.com",
    },
    "xai": {
        "model": "grok-4",
        "supported_api_types": ["Completions"],
        "max_input_tokens": 128000,
        "max_output_tokens": 131072,
        "endpoint": "https://api.x.ai/v1",
    },
    "anthropic": {
        "model": "claude-sonnet-5",
        "supported_api_types": [
            "Completions",
            "Anthropic",  # native Anthropic SDK (requires the `anthropic` package)
        ],  # Completions is the built-in default: Anthropic's OpenAI-compatible
        # /v1/chat/completions. The native Anthropic SDK API type is selectable
        # with --set api-type=Anthropic / --api-type Anthropic (it requires the
        # optional `anthropic` package; see REQUIRES_BY_API_TYPE).
        "max_input_tokens": 200000,
        "max_output_tokens": 64000,
        "endpoint": "https://api.anthropic.com/v1/",
        # Per-API-type endpoints: the OpenAI-compatible Chat Completions URL
        # and the native Anthropic SDK base URL. A provider whose dict holds a
        # single entry uses that URL as the default for *any* API type (unless
        # a config endpoint is set); see get_endpoint_for_api_type.
        "endpoint_by_api_type": {
            "Completions": "https://api.anthropic.com/v1/",
            "Anthropic": "https://api.anthropic.com",
        },
    },
    # Special case: requires an endpoint from config (--set endpoint) and has
    # no built-in default model.
    "custom": {
        "model": None,
        "supported_api_types": ["Completions"],
        "max_input_tokens": None,
        "max_output_tokens": None,
        "endpoint": CUSTOM_ENDPOINT_MARKER,
    },
}

# Optional Python package required by each non-OpenAI API type.
#
# The two built-in API types (``"Responses"`` and ``"Completions"``) are
# served by the ``openai`` package, which is a hard dependency, so they never
# appear here. Any *other* API type listed in a provider's
# ``supported_api_types`` (e.g. ``"Anthropic"`` for the native Anthropic SDK)
# is backed by an optional package declared in this dict, keyed by the
# canonical API type.
#
# When the user attempts to set an API type whose required package is missing,
# the change is aborted with a message naming the package that must be
# installed (see :func:`ensure_api_type_available`).
REQUIRES_BY_API_TYPE: dict[str, str] = {
    "Anthropic": "anthropic",
    "DashScope": "dashscope",
}


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
