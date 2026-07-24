"""FastAPI application factory + ``run_web(args)`` entry point.

At the point ``run_web`` is called, ``__main__.py`` has already:
  - configured logging
  - set ``running_privileges`` from -r -w -x
  - resolved provider/endpoint/model into env vars
  - loaded the API key from auth.json
  - validated required config
"""

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import WebServerConfig
from .session import SessionManager
from .security import add_cors, TokenAuthMiddleware

logger = logging.getLogger(__name__)


def create_app(config: WebServerConfig) -> FastAPI:
    """Build the FastAPI application."""
    from .routers import chat as chat_router
    from .routers import config as config_router
    from .routers import tools as tools_router
    from .routers import mcp as mcp_router

    app = FastAPI(title="Janito Web", version="0.1.0")

    # Store config + session manager on app state
    app.state.config = config
    app.state.sessions = SessionManager(config)

    # Enable toolsets from CLI flags (gmail, onedrive)
    config.apply_toolsets()

    # Optional bearer-token auth (no-op when auth_token is None)
    app.add_middleware(TokenAuthMiddleware, auth_token=config.auth_token)

    # CORS for development
    add_cors(app)

    # API routers
    app.include_router(chat_router.router, prefix="/api/chat", tags=["chat"])
    app.include_router(config_router.router, prefix="/api/config", tags=["config"])
    app.include_router(tools_router.router, prefix="/api/tools", tags=["tools"])
    app.include_router(mcp_router.router, prefix="/api/mcp", tags=["mcp"])

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "model": config.model}

    # Serve frontend (no build step — plain HTML/JS/CSS)
    frontend_dir = Path(__file__).parent.parent / "frontend"
    if frontend_dir.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True))
    else:
        logger.warning(f"Frontend directory not found: {frontend_dir}")

    return app


def run_web(args) -> None:
    """Entry point called from ``__main__.py`` when ``--web`` is passed."""
    import uvicorn

    config = WebServerConfig.from_args(args)
    app = create_app(config)

    url = f"http://{config.host}:{config.port}"

    if config.open_browser:
        import threading
        import webbrowser

        def _open():
            try:
                webbrowser.open(url)
            except Exception as e:
                logger.debug(f"Could not open browser: {e}")

        # Open the browser slightly after the server starts listening
        threading.Timer(0.8, _open).start()

    # Banner (mirrors CLI aesthetics, plain print — no Rich dependency here)
    print(f"Janito Web UI running at {url}")
    print(f"  Model: {config.model or os.getenv('OPENAI_MODEL', '?')}")
    if config.auth_token:
        print("  Auth: bearer token required (JANITO_WEB_TOKEN is set)")
    print("  Press Ctrl+C to stop.")

    try:
        uvicorn.run(app, host=config.host, port=config.port, log_level="warning")
    finally:
        from janito.mcp_manager import shutdown_mcp_manager
        try:
            shutdown_mcp_manager()
        except Exception:
            pass


# Imported lazily at call time to keep the module importable without uvicorn
import os
