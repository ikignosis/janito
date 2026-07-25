"""Configuration endpoints: read/patch runtime config, providers, status."""

import os
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
    provider requires a restart (it's baked into env vars).
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

    # If the model was changed, also update the env so new API calls use it
    if "model" in updated and updated["model"]:
        os.environ["OPENAI_MODEL"] = updated["model"]

    return {"updated": updated}


@router.get("/providers")
async def list_providers(request: Request):
    """List supported providers."""
    from janito.provider_config import list_supported_providers, PROVIDER_BASE_URLS
    return {
        "providers": [
            {"name": name, "base_url": url}
            for name, url in PROVIDER_BASE_URLS.items()
        ]
    }


@router.get("/status")
async def get_status(request: Request):
    """API key status (masked), active provider, privileges."""
    from janito.general_config import get_masked_api_key, get_active_provider
    from janito import privileges as _privileges_mod

    api_key = os.getenv("OPENAI_API_KEY")
    priv = _privileges_mod.running_privileges

    return {
        "api_key": get_masked_api_key(api_key) if api_key else "(not set)",
        "api_key_set": bool(api_key),
        "active_provider": get_active_provider(),
        "model": os.getenv("OPENAI_MODEL"),
        "base_url": os.getenv("OPENAI_BASE_URL"),
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
