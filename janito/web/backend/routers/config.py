"""Configuration endpoints: read/patch runtime config, providers, status."""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_config(request: Request):
    return request.app.state.config


@router.get("")
async def get_config(request: Request):
    """Current runtime config (provider, model, flags from CLI)."""
    config = _get_config(request)
    from janito import privileges as _privileges_mod

    priv = _privileges_mod.running_privileges
    privileges = {
        "read": bool(getattr(priv, "READ", False)) if priv else True,
        "write": bool(getattr(priv, "WRITE", False)) if priv else True,
        "exec": bool(getattr(priv, "EXEC", False)) if priv else True,
        "restricted": priv is not None,
    }

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
        "privileges": privileges,
        "web_host": config.web_host,
        "web_port": config.web_port,
        "auth_required": config.auth_token is not None,
    }


@router.patch("")
async def patch_config(request: Request):
    """Update mutable config values (model, thinking, etc.).

    Only a safe subset of fields is mutable at runtime. Changing the
    provider requires a restart.
    """
    config = _get_config(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON"}, status_code=400)

    mutable = {"model": str, "thinking": bool, "verbose": bool}
    updated = {}
    for key, typ in mutable.items():
        if key in body:
            setattr(config, key, typ(body[key]))
            updated[key] = getattr(config, key)

    return {"updated": updated}


@router.get("/providers")
async def list_providers(request: Request):
    """List supported providers."""
    from janito.provider_config import PROVIDER_BASE_URLS

    return {
        "providers": [
            {"name": name, "base_url": url} for name, url in PROVIDER_BASE_URLS.items()
        ]
    }


@router.get("/status")
async def get_status(request: Request):
    """API key status (masked), active provider, privileges."""
    from janito import privileges as _privileges_mod
    from janito.auth_config import get_api_key
    from janito.general_config import (
        get_active_provider,
        get_masked_api_key,
        load_endpoint_from_config,
    )
    from janito.provider_config import (
        CUSTOM_ENDPOINT_MARKER,
        get_base_url_from_provider,
    )

    config = _get_config(request)
    provider = get_active_provider()

    api_key = get_api_key(provider)

    # Endpoint resolution mirrors the runtime: a configured endpoint override
    # first, otherwise the provider's built-in default (None => standard OpenAI).
    base_url = load_endpoint_from_config(provider)
    if not base_url:
        provider_default = get_base_url_from_provider(provider)
        if provider_default and provider_default != CUSTOM_ENDPOINT_MARKER:
            base_url = provider_default

    priv = _privileges_mod.running_privileges

    return {
        "api_key": get_masked_api_key(api_key) if api_key else "(not set)",
        "api_key_set": bool(api_key),
        "active_provider": provider,
        "model": config.model,
        "base_url": base_url,
        "privileges": {
            "read": bool(getattr(priv, "READ", False)) if priv else True,
            "write": bool(getattr(priv, "WRITE", False)) if priv else True,
            "exec": bool(getattr(priv, "EXEC", False)) if priv else True,
            "restricted": priv is not None,
        },
    }


@router.get("/cli")
async def get_cli_args(request: Request):
    """Show the CLI args the server was started with."""
    config = _get_config(request)
    return {"cli_args": config.cli_args or {}}
