"""
Shared helpers for the config API router.

The patch helpers implement the per-provider mutable fields of the web
Settings drawer (``model``, ``endpoint``, ``api_type``,
``responses_in_server``) and their provider resolution.  They were extracted
from ``janito.web.backend.routers.config`` so the router stays focused on
endpoint wiring.
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
    from janito.provider_config import validate_provider_name

    raw_provider = str(body.get("provider") or "").strip()
    if raw_provider:
        try:
            return validate_provider_name(raw_provider)
        except ValueError as e:
            return JSONResponse({"detail": str(e)}, status_code=400)
    return config.session_provider or config.provider or get_active_provider()


def _patch_model(body, provider, effective, config, updated) -> JSONResponse | None:
    """Apply the ``model`` field; returns an error response or None."""
    if "model" not in body:
        return None

    from janito.general_config import (
        model_config_key,
        set_config_value,
        unset_config_value,
    )

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

    from janito.general_config import (
        endpoint_config_key,
        set_config_value,
        unset_config_value,
    )

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

    from janito.general_config import (
        api_type_config_key,
        normalize_api_type,
        set_config_value,
        unset_config_value,
    )
    from janito.provider_config import ensure_api_type_available

    raw = str(body["api_type"]).strip()

    # Persist per-provider (providers.<name>.api-type), canonicalized to
    # "Responses" / "Completions" / "Anthropic" (rejects anything else
    # with 400). An empty value clears the override so the provider falls
    # back to its built-in default. Native-SDK API types (e.g. "Anthropic")
    # also require their optional package to be installed: when it is
    # missing the change is aborted with 400 (nothing is written) and a
    # message naming the package.
    key = api_type_config_key(provider)
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

    from janito.general_config import responses_in_server_config_key, set_config_value

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

    # Persist per-provider (providers.<name>.responses-in-server) so the
    # CLI's Responses-API path (conversations_api) picks it up.  Only
    # meaningful while the provider's API type is "Responses".
    set_config_value(responses_in_server_config_key(provider), responses_in_server)
    updated["responses_in_server"] = responses_in_server

    return None
