"""MCP service management endpoints."""

import asyncio
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_manager():
    from janito.mcp_manager import get_mcp_manager

    return get_mcp_manager()


@router.get("/services")
async def list_services(request: Request):
    """List configured MCP services + connection status."""
    from janito.mcp_config import list_services as _list_services

    manager = _get_manager()
    connected = set(manager.connected_services)

    services = []
    for name, cfg in _list_services().items():
        transport_type = cfg.get("transport") or cfg.get("type") or "stdio"
        services.append(
            {
                "name": name,
                "connected": name in connected,
                "transport": transport_type,
                "config": {k: v for k, v in cfg.items() if k.lower() not in ("env",)},
            }
        )

    return {"services": services, "connected_count": len(connected)}


@router.post("/services/{name}/connect")
async def connect_service(name: str, request: Request):
    """Connect to an MCP service."""
    manager = _get_manager()
    try:
        await asyncio.to_thread(manager.load_services, [name])
    except Exception as e:
        logger.error(f"Failed to connect MCP service {name}: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)

    return {"name": name, "connected": name in manager.connected_services}


@router.post("/services/{name}/disconnect")
async def disconnect_service(name: str, request: Request):
    """Disconnect an MCP service."""
    manager = _get_manager()
    await asyncio.to_thread(manager.unload_service, name)
    return {"name": name, "connected": name in manager.connected_services}


@router.get("/tools")
async def list_mcp_tools(request: Request):
    """All MCP tools across services."""
    manager = _get_manager()
    try:
        tools = await asyncio.to_thread(manager.get_all_tools, False)
    except Exception as e:
        logger.warning(f"Failed to list MCP tools: {e}")
        tools = []
    return {"tools": tools, "count": len(tools)}
