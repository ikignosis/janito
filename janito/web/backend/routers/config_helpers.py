"""
Shared helpers for the config API router.

The patch helpers implement the per-provider mutable fields of the web
Settings drawer (``model``, ``endpoint``, ``api_type``,
``responses_in_server``) and their provider resolution.  They were extracted
from ``janito.web.backend.routers.config`` so the router stays focused on
endpoint wiring.

``api_type`` and ``responses_in_server`` are **model-scoped**: they are
stored under ``providers.<name>.models.<model>.<key>`` where ``model`` is
the provider's configured model, else its built-in default model.
"""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

# Configure logger for this module
logger = logging.getLogger(__name__)


async def _read_json_body(request: Request):
    """Parse the request body; returns ``(body, error_response)``."""
    try:
        body = await request.json()
    except Exception:
        return None, JSONResponse({"detail": "Invalid JSON"}, status_code=400)
    return body, None


def _resolve_target_provider(body: dict, config):
    """Resolve the provider the per-provider values belong to.

    An explicit ``provider`` from the body (the Settings drawer's selection)
    wins; otherwise the provider the next prompt resolves to.
    """
    from janito.general_config import get_active_provider
    from janito.provider_validation import validate_provider_name

    raw_provider = str(body.get("provider") or "").strip()
    if raw_provider:
        try:
            return validate_provider_name(raw_provider)
        except ValueError as e:
            return JSONResponse({"detail": str(e)}, status_code=400)
    return config.session_provider or config.provider or get_active_provider()


def _entry_model(provider: str) -> str | None:
    """Resolve the model a model-scoped value belongs to for ``provider``.

    The provider's configured model (``providers.<name>.model``) wins, else
    the built-in default model (from the provider's config entry, its
    ``default_model``).  ``None`` means the provider has no usable model
    (e.g. ``custom`` before a model is set).
    """
    from janito.config_loaders import load_model_from_config
    from janito.provider_accessors import get_default_model_from_provider

    return load_model_from_config(provider) or get_default_model_from_provider(provider)


def _patch_model(body, provider, effective, config, updated) -> JSONResponse | None:
    """Apply the ``model`` field; returns an error response or None."""
    if "model" not in body:
        return None

    from janito.config_keys import model_config_key
    from janito.config_store import set_config_value, unset_config_value

    model = str(body["model"]).strip()

    # Persist per-provider so each provider keeps its own default model.
    key = model_config_key(provider)
    if model:
        set_config_value(key, model)
    else:
        unset_config_value(key)
    updated["model"] = model

    # Mirror into the running server only when the change affects the
    # provider the next prompt actually uses; otherwise the server keeps
    # its current model and the new value still lands on disk for the
    # targeted provider.
    if provider == effective:
        config.model = model or None

    return None


def _patch_endpoint(body, provider, effective, config, updated) -> JSONResponse | None:
    """Apply the ``endpoint`` field; returns an error response or None."""
    if "endpoint" not in body:
        return None

    from janito.config_keys import endpoint_config_key
    from janito.config_store import set_config_value, unset_config_value

    endpoint = str(body["endpoint"]).strip()

    # Persist per-provider (providers.<name>.endpoint).  An empty value
    # clears the override so the provider falls back to its built-in
    # endpoint.  No in-memory mirror needed: the OpenAI client resolves
    # the base URL per call, so the very next prompt uses the new value.
    key = endpoint_config_key(provider)
    if endpoint:
        set_config_value(key, endpoint)
    else:
        unset_config_value(key)
    updated["endpoint"] = endpoint

    return None


def _patch_api_type(body, provider, effective, config, updated) -> JSONResponse | None:
    """Apply the ``api_type`` field; returns an error response or None."""
    if "api_type" not in body:
        return None

    from janito.config_keys import model_scoped_config_key, normalize_api_type
    from janito.config_store import set_config_value, unset_config_value
    from janito.provider_accessors import ensure_api_type_available

    raw = str(body["api_type"]).strip()

    # The value is model-scoped: it lands under
    # providers.<name>.models.<model>.api-type for the provider's
    # configured/default model.
    model = _entry_model(provider)
    if model is None:
        return JSONResponse(
            {
                "detail": (
                    f"Provider '{provider}' has no configured or default "
                    "model; set one before changing the API type."
                )
            },
            status_code=400,
        )
    key = model_scoped_config_key(provider, model, "api-type")

    # Persist per provider/model, canonicalized to "Responses" /
    # "Completions" / "Anthropic" / "DashScope" / "Gemini" (rejects
    # anything else with 400). An empty value clears the override so the
    # model falls back to its built-in default. Native-SDK API types (e.g.
    # "Anthropic") also require their optional package to be installed:
    # when it is missing the change is aborted with 400 (nothing is
    # written) and a message naming the package.
    if raw:
        try:
            api_type = normalize_api_type(raw)
        except ValueError as e:
            return JSONResponse({"detail": str(e)}, status_code=400)
        try:
            ensure_api_type_available(api_type)
        except ValueError as e:
            return JSONResponse({"detail": str(e)}, status_code=400)
        set_config_value(key, api_type)
        updated["api_type"] = api_type
    else:
        unset_config_value(key)
        updated["api_type"] = ""

    return None


def _patch_responses_in_server(
    body, provider, effective, config, updated
) -> JSONResponse | None:
    """Apply the ``responses_in_server`` field; returns an error response or None."""
    if "responses_in_server" not in body:
        return None

    from janito.config_keys import model_scoped_config_key
    from janito.config_store import set_config_value

    value = body["responses_in_server"]
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes", "on"):
            value = True
        elif lowered in ("false", "0", "no", "off"):
            value = False
        else:
            return JSONResponse(
                {"detail": "'responses_in_server' must be a boolean"},
                status_code=400,
            )
    responses_in_server = bool(value)

    # The value is model-scoped: it lands under
    # providers.<name>.models.<model>.responses-in-server for the
    # provider's configured/default model, so the CLI's Responses-API
    # path (conversations_api) picks it up.  Only meaningful while the
    # provider's API type is "Responses".
    model = _entry_model(provider)
    if model is None:
        return JSONResponse(
            {
                "detail": (
                    f"Provider '{provider}' has no configured or default "
                    "model; set one before changing responses-in-server."
                )
            },
            status_code=400,
        )
    key = model_scoped_config_key(provider, model, "responses-in-server")
    set_config_value(key, responses_in_server)
    updated["responses_in_server"] = responses_in_server

    return None


def _base_info_for(variant: str):
    """Resolve a registered variant to its ``(canonical_base, base_info)``.

    The base is the variant name's prefix (before the first ``-``) matched
    case-insensitively against the supported providers.

    Args:
        variant: A registered variant name (e.g. ``alibaba-tokenplan``).

    Returns:
        A ``(base_name, base_info)`` tuple; ``base_info`` is ``None`` when the
        prefix does not map to a supported provider.
    """
    from janito.provider_registry import parse_variant_name
    from janito.provider_validation import canonical_provider_name
    from janito.providers import get_provider_config

    base_name = parse_variant_name(variant)[0]
    canonical = canonical_provider_name(base_name)
    if canonical is None:
        return base_name, None
    return canonical, get_provider_config(canonical)


def _build_provider_entry(
    name,
    info,
    *,
    active_provider,
    effective_provider,
    is_variant=False,
    base_provider=None,
):
    """Build one provider entry for the Settings drawer / topbar combo.

    The entry shape is shared by base providers and registered variants; for
    a variant ``info`` is the *base* provider's info entry, so the variant
    inherits the base's built-in defaults while its own per-variant config
    (``providers.<name>.*``) and API key are read off the variant name.

    The ``default_*`` fields (and the plain ``responses_in_server`` /
    ``supported_api_types`` / ``supported_reasoning_levels`` fields) are
    computed for the entry's **effective model**: the configured model
    (``providers.<name>.model``), else the built-in ``default_model``.  A
    ``models`` summary lists every built-in model with its defaults so the
    drawer can show per-model information.

    Args:
        name: The provider (or variant) name.
        info: The provider info dict (the base provider's for a variant).
        active_provider: The persisted default provider (``active: true``).
        effective_provider: The provider the next prompt resolves to
            (``effective: true``).
        is_variant: Whether this entry is a registered variant.
        base_provider: The canonical base provider name for a variant.
    """
    from janito.auth_config import get_api_key
    from janito.config_loaders import (
        load_api_type,
        load_endpoint_from_config,
        load_model_from_config,
        load_responses_in_server_from_config,
    )
    from janito.provider_accessors import (
        get_default_api_type_from_provider,
        get_default_max_input_tokens_from_provider,
        get_default_max_output_tokens_from_provider,
        get_default_reasoning_level_from_provider,
        get_default_thinking_from_provider,
        get_endpoint_for_api_type,
        get_required_package_for_api_type,
        get_responses_in_server_from_provider,
        get_supported_api_types_from_provider,
        get_supported_reasoning_levels_from_provider,
        is_api_type_available,
        requires_explicit_model,
    )
    from janito.provider_registry import ProviderRegistry
    from janito.providers import CUSTOM_ENDPOINT_MARKER

    configured_model = load_model_from_config(name)
    default_model = info.get("default_model")
    # A placeholder "custom" default (e.g. openrouter) is not a usable model:
    # it only carries built-in defaults such as the default API type, so it is
    # not shown as the provider's default model.  The entry's model is the
    # configured override, else the built-in default.
    if default_model and requires_explicit_model(name):
        default_model = None
    entry_model = configured_model or default_model

    # Resolve the effective base URL: a configured endpoint override
    # takes priority, otherwise the provider's built-in default resolved
    # for the entry model's default API type (honors the provider's
    # ``endpoint_by_api_type`` map, e.g. Anthropic's native-SDK URL).
    # ``get_endpoint_for_api_type`` / ``get_default_api_type_from_provider``
    # resolve variants to their base provider automatically.
    endpoint_override = load_endpoint_from_config(name)
    if endpoint_override:
        base_url = endpoint_override
    else:
        built_in_url = get_endpoint_for_api_type(
            name, get_default_api_type_from_provider(name, entry_model)
        )
        if built_in_url and built_in_url != CUSTOM_ENDPOINT_MARKER:
            base_url = built_in_url
        else:
            base_url = None

    api_key = get_api_key(name)

    # Advanced per-provider settings (Settings drawer's Advanced section):
    # the configured ``api_type`` override (``None`` when the model's
    # built-in default applies) and the effective ``responses_in_server``
    # flag (configured override first, else the built-in default).
    api_type_override = load_api_type(name, entry_model)
    responses_in_server = get_responses_in_server_from_provider(name, entry_model)

    # Per-API-type availability for the Settings drawer's API Type
    # combobox.  The OpenAI-SDK types (Responses / Completions) are
    # always available (the `openai` package is a hard dependency);
    # native-SDK types (e.g. ``Anthropic``) are only available while
    # their optional package is installed.  The web UI keeps the
    # unavailable types OUT of the combobox and shows this info instead,
    # so the user sees why a type is missing and how to enable it.
    api_types = []
    supported_api_types = get_supported_api_types_from_provider(name, entry_model) or []
    for api_type in supported_api_types:
        package = get_required_package_for_api_type(api_type)
        available = is_api_type_available(api_type)
        entry = {"type": api_type, "available": available}
        if package is not None:
            entry["required_package"] = package
        if not available:
            entry["reason"] = (
                f"The {api_type} API requires the optional '{package}' "
                f"package, which is not installed. Install it with: "
                f"pip install {package}"
            )
        api_types.append(entry)

    # Per-model summary (name + defaults) so the drawer can show per-model
    # information beyond the entry's effective model.
    registry = ProviderRegistry()
    provider_obj = registry.get(name)
    models_summary = []
    for model_name in provider_obj.model_names() if provider_obj is not None else []:
        models_summary.append(
            {
                "name": model_name,
                "default": model_name == default_model,
                "supported_api_types": get_supported_api_types_from_provider(
                    name, model_name
                ),
                "default_api_type": get_default_api_type_from_provider(
                    name, model_name
                ),
                "max_input_tokens": get_default_max_input_tokens_from_provider(
                    name, model_name
                ),
                "max_output_tokens": get_default_max_output_tokens_from_provider(
                    name, model_name
                ),
                "reasoning_level": get_default_reasoning_level_from_provider(
                    name, model_name
                ),
                "supported_reasoning_levels": get_supported_reasoning_levels_from_provider(
                    name, model_name
                ),
                "thinking": get_default_thinking_from_provider(name, model_name),
                "responses_in_server": get_responses_in_server_from_provider(
                    name, model_name
                ),
            }
        )

    # The built-in (raw) responses-in-server default for the entry's model --
    # NOT the config-overridden effective value, so the drawer can show the
    # built-in default next to the effective flag and the override.
    default_responses_in_server = (
        provider_obj.model_config(entry_model).responses_in_server()
        if provider_obj is not None
        else True
    )

    entry = {
        "name": name,
        "base_url": base_url,
        "model": configured_model,
        "default_model": default_model,
        "api_type": api_type_override,
        "default_api_type": get_default_api_type_from_provider(name, entry_model),
        "supported_api_types": get_supported_api_types_from_provider(name, entry_model),
        "api_types": api_types,
        "endpoint_by_api_type": info.get("endpoint_by_api_type"),
        "responses_in_server": responses_in_server,
        "default_responses_in_server": default_responses_in_server,
        "responses_in_server_override": load_responses_in_server_from_config(
            name, entry_model
        ),
        "default_max_input_tokens": get_default_max_input_tokens_from_provider(
            name, entry_model
        ),
        "default_max_output_tokens": get_default_max_output_tokens_from_provider(
            name, entry_model
        ),
        "default_reasoning_level": get_default_reasoning_level_from_provider(
            name, entry_model
        ),
        "supported_reasoning_levels": get_supported_reasoning_levels_from_provider(
            name, entry_model
        ),
        "default_thinking": get_default_thinking_from_provider(name, entry_model),
        "models": models_summary,
        "endpoint": endpoint_override,
        "api_key_set": bool(api_key),
        "active": name == active_provider,
        "effective": name == effective_provider,
    }
    if is_variant:
        entry["variant"] = True
        entry["base_provider"] = base_provider
    return entry
