"""Configuration endpoints: read/patch runtime config, providers, status."""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

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
        "thinking": config.thinking,
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
    """Update mutable config values (model, etc.).

    Only a safe subset of fields is mutable at runtime. Thinking mode and
    verbose logging are CLI-level flags and cannot be changed here; the
    default provider is changed via ``POST /api/config/default-provider``.
    """
    config = _get_config(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON"}, status_code=400)

    # ``thinking`` and ``verbose`` are CLI-level flags that cannot be
    # meaningfully toggled at runtime, so they are intentionally excluded
    # from the mutable set.
    mutable = {"model": str}
    updated = {}
    for key, typ in mutable.items():
        if key in body:
            setattr(config, key, typ(body[key]))
            updated[key] = getattr(config, key)

    return {"updated": updated}


@router.get("/providers")
async def list_providers(request: Request):
    """List all supported providers with their per-provider configuration.

    Each entry aggregates data from the existing janito modules:

    * ``provider_config.PROVIDER_INFO`` — the built-in per-provider defaults
      (``endpoint``, ``default_model`` and ``default_context_window_size``).
      ``endpoint`` is ``None`` for standard OpenAI and the ``CUSTOM_ENDPOINT``
      marker for "custom".
    * ``general_config`` — the per-provider ``model`` and ``endpoint``
      overrides stored in ``~/.janito/config.json`` under
      ``providers.<name>.{model,endpoint}``.
    * ``auth_config.get_api_key()`` — whether an API key exists for the
      provider in ``~/.janito/auth.json`` (the key itself is never sent;
      only ``api_key_set: bool``).
    * ``general_config.get_active_provider()`` — the currently active
      provider (``active: true`` on that entry).
    """
    from janito.auth_config import get_api_key
    from janito.general_config import (
        get_active_provider,
        load_endpoint_from_config,
        load_model_from_config,
    )
    from janito.provider_config import CUSTOM_ENDPOINT_MARKER, PROVIDER_INFO

    active_provider = get_active_provider()

    providers = []
    for name, info in PROVIDER_INFO.items():
        built_in_url = info.get("endpoint")
        # Resolve the effective base URL: a configured endpoint override
        # takes priority, otherwise the provider's built-in default.
        endpoint_override = load_endpoint_from_config(name)
        if endpoint_override:
            base_url = endpoint_override
        elif built_in_url and built_in_url != CUSTOM_ENDPOINT_MARKER:
            base_url = built_in_url
        else:
            base_url = None

        api_key = get_api_key(name)

        providers.append(
            {
                "name": name,
                "base_url": base_url,
                "model": load_model_from_config(name),
                "default_model": info.get("default_model"),
                "default_context_window_size": info.get("default_context_window_size"),
                "endpoint": endpoint_override,
                "api_key_set": bool(api_key),
                "active": name == active_provider,
            }
        )

    return {"providers": providers}


@router.post("/default-provider")
async def set_default_provider(request: Request):
    """Promote a provider to the default (persisted in ``~/.janito/config.json``).

    Web counterpart of ``janito --set provider=<name>``: the value is written
    to the config file so future CLI *and* web runs pick it up, and it is
    also mirrored into this running server's config so the next prompt
    resolves the new provider without a restart.
    """
    from janito.general_config import load_model_from_config, set_config_value
    from janito.provider_config import validate_provider_name

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON"}, status_code=400)

    raw = str(body.get("provider") or "").strip()
    if not raw:
        return JSONResponse({"detail": "Missing 'provider'"}, status_code=400)

    try:
        provider = validate_provider_name(raw)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)

    # Persist as the default for all future runs.
    set_config_value("provider", provider)

    # Mirror into this running server: provider resolution now picks up the
    # new default.  Also adopt the new provider's configured model — keeping
    # a model that belongs to the previous provider would make the next API
    # call fail.  (An explicitly pinned --model was already baked into
    # config.model at startup; runtime overrides via PATCH /api/config are
    # intentionally replaced here.)
    config = _get_config(request)
    config.provider = provider
    try:
        config.model = load_model_from_config(provider)
    except Exception:
        config.model = None

    logger.info(f"Default provider set to '{provider}' (model: {config.model})")
    return {"provider": provider, "model": config.model}


@router.post("/api-key")
async def set_provider_api_key(request: Request):
    """Store an API key for a provider (persisted in ``~/.janito/auth.json``).

    Web counterpart of ``janito --set-api-key <key> --provider <name>``:
    the key is written to the auth file (mode ``0600``) so both CLI and web
    runs pick it up.  The OpenAI client resolves the key per call, so the
    next prompt already uses it — no restart needed.  The raw key is never
    echoed back; only the masked form (same as ``/status``) is returned.
    """
    from janito.auth_config import set_api_key
    from janito.general_config import get_masked_api_key
    from janito.provider_config import validate_provider_name

    try:
        body = await request.json()
    except Exception:
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
    from janito.general_config import (
        get_active_provider,
        get_masked_api_key,
        load_endpoint_from_config,
    )
    from janito.provider_config import (
        CUSTOM_ENDPOINT_MARKER,
        get_base_url_from_provider,
        validate_provider_name,
    )

    config = _get_config(request)
    active = get_active_provider()

    target = active
    if provider:
        try:
            target = validate_provider_name(provider)
        except ValueError as e:
            return JSONResponse({"detail": str(e)}, status_code=400)

    api_key = get_api_key(target)

    # Endpoint resolution mirrors the runtime: a configured endpoint override
    # first, otherwise the provider's built-in default (None => standard OpenAI).
    base_url = load_endpoint_from_config(target)
    if not base_url:
        provider_default = get_base_url_from_provider(target)
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
