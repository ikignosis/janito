"""Tool introspection endpoints."""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("")
async def list_tools(request: Request):
    """List all loaded tools + schemas + permissions."""
    from janito.tooling.tools_registry import (
        get_all_tool_schemas, get_all_tool_permissions,
    )
    schemas = get_all_tool_schemas()
    permissions = get_all_tool_permissions()

    tools = []
    for schema in schemas:
        fn = schema.get("function", {})
        name = fn.get("name", "")
        tools.append({
            "name": name,
            "description": fn.get("description", ""),
            "permissions": permissions.get(name, ""),
            "parameters": fn.get("parameters", {}),
        })

    return {"tools": tools, "count": len(tools)}


@router.get("/skipped")
async def list_skipped_tools(request: Request):
    """Tools skipped during discovery + reasons."""
    from janito.tools import get_skipped_tools
    return {"skipped": get_skipped_tools()}


@router.post("/toolsets/{name}")
async def add_toolset(name: str, request: Request):
    """Dynamically add a toolset (gmail, onedrive...)."""
    from janito.tooling.tools_registry import add_toolset as _add_toolset
    ok = _add_toolset(name)
    return {"toolset": name, "added": ok}
