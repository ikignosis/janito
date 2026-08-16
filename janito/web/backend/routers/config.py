"""Configuration endpoints: read/patch runtime config, providers, status."""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .config_helpers import (
    _base_info_for,
    _build_provider_entry,
    _patch_api_type,
    _patch_endpoint,
    _patch_model,
    _patch_responses_in_server,
    _read_json_body,
    _resolve_target_provider,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_config(request: Request):
    return request.app.state.config


def _privileges_dict() -> dict:
    """Effective runtime privileges (from -r/-w/-x CLI flags).

    Shared by the ``/`` and ``/status`` endpoints so the wire format
    stays identical everywhere.
    """
    from janito import privileges as _privileges_mod

    priv = _privileges_mod.running_privileges
    return {
        "read": bool(getattr(priv, "READ", False)) if priv else True,
        "write": bool(getattr(priv, "WRITE", False)) if priv else True,
        "exec": bool(getattr(priv, "EXEC", False)) if priv else True,
        "restricted": priv is not None,
    }


@router.get("")
async def get_config(request: Request):
    """Current runtime config (provider, model, flags from CLI)."""
    config = _get_config(request)
    return {
        "provider": config.provider,
        "model": config.model,
        # The frontend treats thinking as an on/off boolean; the raw
        # effective value may be a provider-default dict (e.g. MiniMax-M3's
        # {'type': 'adaptive'}), which is truthy => thinking on.
        "thinking": bool(config.effective_thinking),
        "gmail": config.gmail,
        "onedrive": config.onedrive,
        "no_tools": config.no_tools,
        "no_system_prompt": config.no_system_prompt,
        "verbose": config.verbose,
        "no_history": config.no_history,
        "privileges": _privileges_dict(),
        "web_host": config.web_host,
        "web_port": config.web_port,
        "auth_required": config.auth_token is not None,
    }


@router.patch("")
async def patch_config(request: Request):
    """Update mutable config values and persist them to ``~/.janito/config.json``.

    Only a safe subset of fields is mutable at runtime. Thinking mode and
    verbose logging are CLI-level flags and cannot be changed here; the
    default provider is changed via ``POST /api/config/default-provider``.

    Every mutable field is *provider-scoped*: it is stored per provider under
    ``providers.<name>.<key>`` in ``config.json`` (mirroring the CLI's
    ``--set ...``), so each provider keeps its own values.  Pass ``provider``
    in the body to target a specific provider (the one selected in the
    Settings drawer); when omitted, the value is applied to the provider the
    next prompt resolves to (a session override, else the persisted default).
    The value is written to disk so future CLI *and* web runs pick it up.
    An empty ``model`` / ``endpoint`` / ``api_type`` clears the per-provider
    override (the provider falls back to its built-in default).

    Supported fields:

    * ``model`` -- per-provider default model (``providers.<name>.model``).
      An empty value clears the override.  Mirrored into the running server
      when it affects the provider currently in use.
    * ``endpoint`` -- per-provider base-URL override
      (``providers.<name>.endpoint``).  An empty value clears the override
      (falls back to the provider's built-in endpoint).  The OpenAI client
      resolves the base URL per call, so the next prompt already uses it.
    * ``api_type`` -- per-provider API type (``providers.<name>.api-type``),
      ``"Responses"`` or ``"Completions"`` (case-insensitive, canonicalized).
      An empty value clears the override (falls back to the provider's
      built-in default -- its ``default_api_type`` entry).
    * ``responses_in_server`` -- per-provider override of whether the
      provider's Responses API keeps conversation state server-side
      (``providers.<name>.responses-in-server``).  Accepts ``true``/``false``
      (also ``1``/``0``/``yes``/``no``/``on``/``off``).  Only meaningful when
      the provider's API type is ``Responses``.
    """
    from janito.general_config import get_active_provider

    config = _get_config(request)
    body, error = await _read_json_body(request)
    if error:
        return error

    # ``thinking`` and ``verbose`` are CLI-level flags, so they are
    # intentionally excluded from this persisted mutable set.  Thinking can
    # still be toggled for the running server only via POST /api/config/thinking.
    updated = {}

    mutable_fields = [
        field
        for field in ("model", "endpoint", "api_type", "responses_in_server")
        if field in body
    ]
    if not mutable_fields:
        return {"updated": updated}

    provider = _resolve_target_provider(body, config)
    if isinstance(provider, JSONResponse):
        return provider

    effective = config.session_provider or config.provider or get_active_provider()

    for patcher in (
        _patch_model,
        _patch_endpoint,
        _patch_api_type,
        _patch_responses_in_server,
    ):
        error = patcher(body, provider, effective, config, updated)
        if error:
            return error

    return {"updated": updated}


@router.post("/thinking")
async def set_thinking(request: Request):
    """Toggle thinking mode for this server session (in-memory only).

    Web counterpart of the CLI's ``--thinking`` flag, scoped to the running
    server: the status-bar "thinking" badge posts here and the new value
    applies to the very next prompt.  Like the session-provider override it
    is kept **in memory only** -- ``~/.janito/config.json`` is left
    untouched, so it does not leak into future CLI or web runs and is lost
    when the server restarts.

    The override *forces* the state in both directions: ``false`` disables
    thinking even for providers that reason by default (DeepSeek, Qwen).
    A body of ``{"thinking": true|false}`` sets the state explicitly; an
    empty body (or ``{"toggle": true}``) flips the current effective value.
    """
    config = _get_config(request)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 - treat an unreadable body as empty
        logger.debug("Failed to read request body", exc_info=True)
        body = None

    if isinstance(body, dict) and "thinking" in body:
        value = bool(body["thinking"])
    else:
        # The effective value may be a provider-default dict (e.g. MiniMax-M3's
        # {'type': 'adaptive'}); coerce to a plain bool before flipping.
        value = not bool(config.effective_thinking)
    config.thinking_override = value

    logger.info(f"Runtime thinking set to {value} (in-memory, not persisted)")
    return {
        "thinking": value,
        "effective": config.effective_thinking,
        "persisted": False,
    }


@router.get("/providers")
async def list_providers(request: Request):
    """List all supported providers with their per-provider configuration.

    Each entry aggregates data from the existing janito modules:

    * ``janito.providers.get_provider_config`` -- the built-in per-provider
      defaults
      (``endpoint``, ``model``, ``max_input_tokens``, ``max_output_tokens``,
      ``reasoning_level``, ``supported_reasoning_levels`` and ``thinking``).
      ``endpoint`` is ``None`` for standard OpenAI and the ``CUSTOM_ENDPOINT``
      marker for "custom".
    * ``config_store`` -- the per-provider ``model`` and ``endpoint``
      overrides stored in ``~/.janito/config.json`` under
      ``providers.<name>.{model,endpoint}``.
    * ``auth_config.get_api_key()`` -- whether an API key exists for the
      provider in ``~/.janito/auth.json`` (the key itself is never sent;
      only ``api_key_set: bool``).
    * ``general_config.get_active_provider()`` -- the persisted default
      provider (``active: true`` on that entry).
    * ``config.session_provider`` -- a session-only override picked from the
      chat-page combo (never written to disk); the provider that the next
      prompt actually uses is flagged ``effective: true``.
    * ``api_types`` -- per-API-type availability for the Settings drawer's
      API Type combobox.  Each entry is ``{type, available}`` plus, for
      optional-package types, ``required_package`` and (when the package is
      missing) a ``reason`` with the install hint.  Unavailable types are
      kept out of the combobox and surfaced as info instead.
    """
    from janito.general_config import get_active_provider
    from janito.provider_validation import list_supported_providers, list_variants
    from janito.providers import get_provider_config

    config = _get_config(request)
    active_provider = get_active_provider()
    session_provider = config.session_provider
    # The provider the next prompt resolves to: the session override wins
    # over the persisted default.
    effective_provider = session_provider or active_provider

    providers = [
        _build_provider_entry(
            name,
            get_provider_config(name),
            active_provider=active_provider,
            effective_provider=effective_provider,
        )
        for name in list_supported_providers()
    ]

    # Registered provider variants (<provider>-<word>): each inherits its
    # base provider's info entry (built-in defaults) while keeping its own
    # per-variant config and API key.  The Settings drawer and topbar combo
    # consume the same fields as base providers, so variants are appended
    # with the same shape plus ``variant`` / ``base_provider`` markers.
    for variant in list_variants():
        base_name, base_info = _base_info_for(variant)
        if base_info is not None:
            providers.append(
                _build_provider_entry(
                    variant,
                    base_info,
                    active_provider=active_provider,
                    effective_provider=effective_provider,
                    is_variant=True,
                    base_provider=base_name,
                )
            )

    return {"providers": providers, "session_provider": session_provider}


@router.post("/session-provider")
async def set_session_provider(request: Request):
    """Switch the provider for this browser/server session only.

    Triggered by the chat-page topbar combo: the chosen provider becomes the
    one used by the next prompt, but the change is kept **in memory only** --
    ``~/.janito/config.json`` is left untouched, so it does not leak into
    future CLI or web runs and is lost when the server restarts.  (The
    Settings drawer's explicit "Set Default" button is the persisting
    counterpart and still uses ``POST /api/config/default-provider``.)

    A provider without an API key stored in ``~/.janito/auth.json`` is
    rejected with ``400`` -- switching to it would only make the next prompt
    fail with an authentication error.  The combo relies on this guard (it
    lists exactly the providers with a key set).
    """
    from janito.auth_config import get_api_key
    from janito.config_loaders import load_model_from_config
    from janito.provider_validation import validate_provider_name

    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 - unreadable body is a client error
        logger.debug("Failed to read request body", exc_info=True)
        return JSONResponse({"detail": "Invalid JSON"}, status_code=400)

    raw = str(body.get("provider") or "").strip()
    if not raw:
        return JSONResponse({"detail": "Missing 'provider'"}, status_code=400)

    try:
        provider = validate_provider_name(raw)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)

    if not get_api_key(provider):
        return JSONResponse(
            {
                "detail": (
                    f"No API key is set for provider '{provider}'. "
                    "Set one first (Settings -> Set API Key, or the CLI's "
                    "--set-api-key) before switching to it."
                )
            },
            status_code=400,
        )

    # In-memory only: nothing is written to ~/.janito/config.json here.
    # Adopt the new provider's configured model too -- keeping a model that
    # belongs to the previous provider would make the next API call fail.
    config = _get_config(request)
    config.session_provider = provider
    try:
        config.model = load_model_from_config(provider)
    except Exception:  # noqa: BLE001 - provider may simply have no configured model
        logger.debug(
            "Could not load a configured model for provider '%s'",
            provider,
            exc_info=True,
        )
        config.model = None

    logger.info(
        f"Session provider set to '{provider}' (model: {config.model}, not persisted)"
    )
    return {"provider": provider, "model": config.model, "persisted": False}


@router.post("/default-provider")
async def set_default_provider(request: Request):
    """Promote a provider to the default (persisted in ``~/.janito/config.json``).

    Web counterpart of ``janito --set provider=<name>``: the value is written
    to the config file so future CLI *and* web runs pick it up, and it is
    also mirrored into this running server's config so the next prompt
    resolves the new provider without a restart.

    A provider without an API key stored in ``~/.janito/auth.json`` is
    rejected with ``400``: promoting it would only make the next prompt fail
    with an authentication error.  The web UI's provider lists rely on this
    guard (they list exactly the providers with a key set).
    """
    from janito.auth_config import get_api_key
    from janito.config_loaders import load_model_from_config
    from janito.config_store import set_config_value
    from janito.provider_validation import validate_provider_name

    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 - unreadable body is a client error
        logger.debug("Failed to read request body", exc_info=True)
        return JSONResponse({"detail": "Invalid JSON"}, status_code=400)

    raw = str(body.get("provider") or "").strip()
    if not raw:
        return JSONResponse({"detail": "Missing 'provider'"}, status_code=400)

    try:
        provider = validate_provider_name(raw)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)

    if not get_api_key(provider):
        return JSONResponse(
            {
                "detail": (
                    f"No API key is set for provider '{provider}'. "
                    "Set one first (Settings -> Set API Key, or the CLI's "
                    "--set-api-key) before making it the default."
                )
            },
            status_code=400,
        )

    # Persist as the default for all future runs.
    set_config_value("provider", provider)

    # Mirror into this running server: provider resolution now picks up the
    # new default.  Also adopt the new provider's configured model -- keeping
    # a model that belongs to the previous provider would make the next API
    # call fail.  (An explicitly pinned --model was already baked into
    # config.model at startup; runtime overrides via PATCH /api/config are
    # intentionally replaced here.)  Clear any transient session override so
    # the freshly persisted default is what's actually in use.
    config = _get_config(request)
    config.session_provider = None
    config.provider = provider
    try:
        config.model = load_model_from_config(provider)
    except Exception:  # noqa: BLE001 - provider may simply have no configured model
        logger.debug(
            "Could not load a configured model for provider '%s'",
            provider,
            exc_info=True,
        )
        config.model = None

    logger.info(f"Default provider set to '{provider}' (model: {config.model})")
    return {"provider": provider, "model": config.model}


@router.post("/api-key")
async def set_provider_api_key(request: Request):
    """Store an API key for a provider (persisted in ``~/.janito/auth.json``).

    Web counterpart of ``janito --set-api-key <key> --provider <name>``:
    the key is written to the auth file (mode ``0600``) so both CLI and web
    runs pick it up.  The OpenAI client resolves the key per call, so the
    next prompt already uses it -- no restart needed.  The raw key is never
    echoed back; only the masked form (same as ``/status``) is returned.
    """
    from janito.auth_config import set_api_key
    from janito.config_keys import get_masked_api_key
    from janito.provider_validation import validate_provider_name

    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 - unreadable body is a client error
        logger.debug("Failed to read request body", exc_info=True)
        return JSONResponse({"detail": "Invalid JSON"}, status_code=400)

    raw_provider = str(body.get("provider") or "").strip()
    if not raw_provider:
        return JSONResponse({"detail": "Missing 'provider'"}, status_code=400)

    try:
        provider = validate_provider_name(raw_provider)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)

    api_key = str(body.get("api_key") or "").strip()
    if not api_key:
        return JSONResponse({"detail": "Missing 'api_key'"}, status_code=400)

    if not set_api_key(provider, api_key):
        return JSONResponse(
            {"detail": "Failed to write the API key to the auth file"},
            status_code=500,
        )

    masked = get_masked_api_key(api_key)
    logger.info(f"API key updated for provider '{provider}' ({masked})")
    return {"provider": provider, "api_key_set": True, "masked": masked}


@router.get("/status")
async def get_status(request: Request, provider: str | None = None):
    """API key status (masked), active provider, privileges.

    By default the status describes the *active* (default) provider.  Pass
    ``?provider=<name>`` to inspect another provider instead (used by the
    settings drawer when a non-default provider is picked in the combobox);
    ``active_provider`` keeps reporting the true default either way.
    """
    from janito.auth_config import get_api_key
    from janito.config_keys import get_masked_api_key
    from janito.config_loaders import load_endpoint_from_config
    from janito.general_config import get_active_provider
    from janito.provider_accessors import (
        get_default_api_type_from_provider,
        get_endpoint_for_api_type,
    )
    from janito.provider_validation import validate_provider_name
    from janito.providers import CUSTOM_ENDPOINT_MARKER

    config = _get_config(request)
    active = get_active_provider()

    # By default describe the *effective* provider -- a session override from
    # the chat-page combo wins over the persisted default.  ``active_provider``
    # keeps reporting the true persisted default either way.
    target = config.session_provider or active
    if provider:
        try:
            target = validate_provider_name(provider)
        except ValueError as e:
            return JSONResponse({"detail": str(e)}, status_code=400)

    api_key = get_api_key(target)

    # Endpoint resolution mirrors the runtime: a configured endpoint override
    # first, otherwise the provider's built-in default resolved for its
    # default API type (None => standard OpenAI).
    base_url = load_endpoint_from_config(target)
    if not base_url:
        provider_default = get_endpoint_for_api_type(
            target, get_default_api_type_from_provider(target)
        )
        if provider_default and provider_default != CUSTOM_ENDPOINT_MARKER:
            base_url = provider_default

    return {
        "api_key": get_masked_api_key(api_key) if api_key else "(not set)",
        "api_key_set": bool(api_key),
        "active_provider": active,
        "provider": target,
        "model": config.model,
        "base_url": base_url,
        "privileges": _privileges_dict(),
    }


@router.get("/cli")
async def get_cli_args(request: Request):
    """Show the CLI args the server was started with."""
    config = _get_config(request)
    return {"cli_args": config.cli_args or {}}
