"""
Module-level provider accessors.

Thin delegating functions over :class:`ProviderRegistry` for the historical
``get_*_from_provider`` API.  Part of the split provider-config module
family.
"""

from .provider_registry import _registry


def get_provider_config(provider: str, model: str | None = None) -> dict | None:
    """
    Get the config entry for a given provider, or for one of its models.

    Without ``model`` this returns the provider's full entry (provider-level
    fields plus its ``models`` dict); with ``model`` it returns just that
    model's entry *within* the provider.  Registered provider variants resolve
    to their base provider's entry.

    Args:
        provider: The provider name (case-insensitive)
        model: The model name. ``None`` returns the whole provider entry.

    Returns:
        The provider config dict if found, the model entry if ``model`` is
        given and has a built-in entry, ``None`` otherwise.
    """
    found = _registry.get(provider)
    if found is None:
        return None
    info = found.info
    if model is None:
        return info
    models = info.get("models", {})
    if not isinstance(models, dict):
        return None
    return models.get(model)


def get_base_url_from_provider(provider: str) -> str | None:
    """
    Get the base URL (endpoint) for a given provider name.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The base URL if found, None otherwise.
        For "custom" provider, returns the "CUSTOM_ENDPOINT" marker.
    """
    found = _registry.get(provider)
    if found is None:
        return None
    return found.info.get("endpoint")


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
    found = _registry.get(provider)
    if found is None:
        return None
    return found.info.get("endpoint_by_api_type")


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
    found = _registry.get(provider)
    if found is None:
        return None
    return found.endpoint_for(api_type)


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
    return sorted(set(("Responses", "Completions")) | set(_registry.requires))


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
    for key, package in _registry.requires.items():
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
    found = _registry.get(provider)
    return found.default_model() if found is not None else None


def get_default_max_output_tokens_from_provider(
    provider: str, model: str | None = None
) -> int | None:
    """
    Get the built-in default max output tokens for a provider's model.

    Args:
        provider: The provider name (case-insensitive)
        model: The model name. ``None`` means the provider's default model.

    Returns:
        The default max output tokens if the model has one, ``None``
        otherwise (either the provider is unknown or the model has no
        built-in default).
    """
    found = _registry.get(provider)
    return found.max_output_tokens(model) if found is not None else None


def get_default_max_input_tokens_from_provider(
    provider: str, model: str | None = None
) -> int | None:
    """
    Get the built-in default max input tokens for a provider's model.

    Args:
        provider: The provider name (case-insensitive)
        model: The model name. ``None`` means the provider's default model.

    Returns:
        The default max input tokens if the model has one, ``None``
        otherwise (either the provider is unknown or the model has no
        built-in default).
    """
    found = _registry.get(provider)
    return found.max_input_tokens(model) if found is not None else None


def get_default_reasoning_level_from_provider(
    provider: str, model: str | None = None
) -> str | None:
    """
    Get the built-in default reasoning level for a provider's model.

    This is the reasoning level/effort used by default when the model
    supports configurable reasoning depth (e.g. ``xhigh`` for Alibaba's
    ``qwen3.8-max``).

    Args:
        provider: The provider name (case-insensitive)
        model: The model name. ``None`` means the provider's default model.

    Returns:
        The default reasoning level if the model has one, ``None``
        otherwise (either the provider is unknown or the model has no
        built-in default).
    """
    found = _registry.get(provider)
    return found.reasoning_level(model) if found is not None else None


def get_supported_reasoning_levels_from_provider(
    provider: str, model: str | None = None
) -> list | None:
    """
    Get the supported reasoning levels for a provider's model.

    Each entry is a dict with an ``effort`` key and a human-readable
    ``description``, describing the reasoning depths the model supports
    (e.g. ``low``/``medium``/``xhigh`` for Alibaba's ``qwen3.8-max``).

    Args:
        provider: The provider name (case-insensitive)
        model: The model name. ``None`` means the provider's default model.

    Returns:
        The list of supported reasoning levels if the model declares them,
        ``None`` otherwise (either the provider is unknown or the model has
        no configurable reasoning).
    """
    found = _registry.get(provider)
    return found.supported_reasoning_levels(model) if found is not None else None


def get_default_thinking_from_provider(provider: str, model: str | None = None):
    """
    Get the built-in default for thinking mode for a provider's model.

    Returns the raw ``thinking`` value from the model entry: a plain
    ``True`` flag for models that reason by default (DeepSeek, Alibaba/Qwen),
    a pass-through dict for models whose API takes a structured thinking
    parameter (MiniMax-M3: ``{'type': 'adaptive'}``), or ``False`` when no
    default exists.  The CLI ``--thinking`` flag still forces thinking on
    explicitly.  Use :func:`apply_thinking_to_extra_body` to turn the value
    into the API call's ``extra_body`` payload.

    Args:
        provider: The provider name (case-insensitive)
        model: The model name. ``None`` means the provider's default model.

    Returns:
        The model's built-in thinking default (``True``, a dict, or ``False``),
        or ``False`` for unknown providers.
    """
    found = _registry.get(provider)
    return found.default_thinking(model) if found is not None else False


def apply_thinking_to_extra_body(call_kwargs: dict, thinking) -> None:
    """Add the resolved thinking mode to ``call_kwargs``' ``extra_body``.

    Thinking values may be:

    - ``True`` -- the flag-style providers (DeepSeek, Alibaba/Qwen) send
      ``extra_body={'enable_thinking': True}``;
    - a **dict** -- passed through verbatim as ``extra_body['thinking']``
      (e.g. MiniMax-M3's ``{'type': 'adaptive'}``, which its
      OpenAI-compatible API accepts with ``type`` ``disabled``/``adaptive``);
    - falsy (``False`` / ``None``) -- nothing is sent.

    The ``call_kwargs`` dict is mutated in place; ``extra_body`` is created
    when needed.
    """
    if thinking is True:
        call_kwargs.setdefault("extra_body", {})["enable_thinking"] = True
    elif isinstance(thinking, dict):
        call_kwargs.setdefault("extra_body", {})["thinking"] = dict(thinking)


def format_thinking_display(thinking) -> str:
    """Render a thinking value for human-readable display.

    ``True`` (or any truthy non-dict) renders as ``"enabled"``; a structured
    dict (e.g. MiniMax-M3's ``{'type': 'adaptive'}``) renders as
    ``"enabled (<type>)"``; falsy values render as ``"disabled"``.
    """
    if isinstance(thinking, dict) and thinking.get("type"):
        return f"enabled ({thinking['type']})"
    return "enabled" if thinking else "disabled"


def get_supported_api_types_from_provider(
    provider: str, model: str | None = None
) -> list[str] | None:
    """
    Get the list of API types a provider's model supports.

    Each entry declares which API types it can talk to: ``"Responses"``
    (the Responses API, ``client.responses.create``) and/or
    ``"Completions"`` (the Chat Completions API,
    ``client.chat.completions.create``), plus native-SDK types such as
    ``"Anthropic"``/``"DashScope"``.

    Args:
        provider: The provider name (case-insensitive)
        model: The model name. ``None`` means the provider's default model.

    Returns:
        The list of supported API types (e.g. ``["Responses", "Completions"]``
        for OpenAI's default model), ``None`` if the provider is unknown or
        the model has no built-in entry.
    """
    found = _registry.get(provider)
    return found.supported_api_types(model) if found is not None else None


def get_default_api_type_from_provider(
    provider: str, model: str | None = None
) -> str | None:
    """
    Get the built-in default API type for a provider's model.

    The default is the **first** entry of the model's
    ``supported_api_types`` list (e.g. ``"Responses"`` for OpenAI's default
    model). The effective API type can be overridden per provider/model with
    ``--set api-type=...`` or per-call with ``--api-type``.

    Args:
        provider: The provider name (case-insensitive)
        model: The model name. ``None`` means the provider's default model.

    Returns:
        The default API type (e.g. ``"Responses"`` or ``"Completions"``), or
        ``None`` if the provider is unknown or the model declares no
        supported types.
    """
    found = _registry.get(provider)
    return found.default_api_type(model) if found is not None else None


def get_responses_in_server_from_provider(
    provider: str, model: str | None = None
) -> bool:
    """
    Get whether a provider's model Responses API keeps conversation state server-side.

    When ``True`` (e.g. OpenAI), the Responses endpoint stores the
    conversation and turns are chained with ``previous_response_id``. When
    ``False`` (e.g. DeepSeek), the ``/responses`` endpoint is **stateless**:
    it cannot resolve a previous response id, so the client must track and
    re-send the entire conversation history on every request (like Chat
    Completions).

    A per-provider/model override stored in ``~/.janito/config.json`` under
    ``providers.<name>.models.<model>.responses-in-server`` (set from the
    CLI with ``--set responses-in-server=...`` or from the web Settings
    drawer's Advanced section) wins over the built-in default, so providers
    that ship a default can still be flipped per deployment.

    Args:
        provider: The provider name (case-insensitive)
        model: The model name. ``None`` means the provider's default model.

    Returns:
        ``True`` if the Responses API keeps server-side state, ``False`` if
        it is stateless. Defaults to ``True`` for models that do not declare
        the flag (the Responses API design) and for unknown providers.
    """
    found = _registry.get(provider)
    if found is None:
        return True
    return found.responses_in_server(model)


def get_provider_cost(
    provider: str, model: str, input: int, output: int, cached: int
) -> str:
    """
    Get the estimated monetary cost of a request for a provider's model.

    The cost is computed by the provider's ``cost.py`` module
    (``janito.providers.<name>.cost``), which exports a
    ``get_cost(model, input, output, cached)`` function returning a
    dollar-formatted string (e.g. ``"1$"``).  Providers without a cost
    module fall back to ``"N/A"``.

    Args:
        provider: The provider name (case-insensitive).  Registered provider
            variants (``<provider>-<word>``) resolve to their base
            provider's cost module.
        model: The model name.
        input: The number of input tokens.
        output: The number of output tokens.
        cached: The number of cached input tokens.

    Returns:
        The estimated cost formatted as a dollar string (e.g. ``"1$"``), or
        ``"N/A"`` when the provider is unknown or has no cost module.
    """
    found = _registry.get(provider)
    if found is None:
        return "N/A"
    base = found.base_name or found.name
    try:
        from importlib import import_module

        cost_module = import_module(f"janito.providers.{base}.cost")
        get_cost = getattr(cost_module, "get_cost")
        return get_cost(model, input, output, cached)
    except (ImportError, AttributeError, TypeError):
        return "N/A"
