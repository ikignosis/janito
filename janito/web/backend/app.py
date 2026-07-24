"""FastAPI application factory + ``run_web(args)`` entry point.

At the point ``run_web`` is called, ``__main__.py`` has already:
  - configured logging
  - set ``running_privileges`` from -r -w -x
  - resolved provider/endpoint/model into env vars
  - loaded the API key from auth.json
  - validated required config
"""

import json
import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
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
        # Serve index.html via a dynamic route so we can inject the auth
        # token (window.__JANITO_TOKEN__) needed by websocket.js / api.js
        # when JANITO_WEB_TOKEN is set. Without this the WS handshake is
        # rejected by TokenAuthMiddleware and the UI shows "Not connected".
        index_file = frontend_dir / "index.html"

        if index_file.exists():
            _base_html = index_file.read_text(encoding="utf-8")
            _token_script = (
                "<script>window.__JANITO_TOKEN__ = "
                + json.dumps(config.auth_token)
                + ";</script>"
            )
            _served_html = _base_html.replace("</head>", _token_script + "\n</head>", 1)

            @app.get("/", response_class=HTMLResponse, include_in_schema=False)
            async def serve_index():
                return HTMLResponse(_served_html)

        # Mount everything else (css/, js/, favicon, etc.) as static files.
        # html=False so "/" is handled by our dynamic route above.
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=False))
    else:
        logger.warning(f"Frontend directory not found: {frontend_dir}")

    return app


def _ensure_web_logging(args) -> None:
    """Make web-backend diagnostic logs visible.

    The default CLI logging setup (``setup_logging`` with no ``--log``) leaves
    the root logger without handlers and above CRITICAL, which silently drops
    the ``logger.warning`` diagnostics added for the WebSocket/auth path.
    When no explicit ``--log`` is given, install a stderr handler at WARNING so
    those messages show up while debugging connection issues.
    """
    if getattr(args, "log", None):
        return  # user configured logging explicitly; leave it alone
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(levelname)s: %(name)s: %(message)s")
        )
        root.addHandler(handler)
        root.setLevel(logging.WARNING)


def run_web(args) -> None:
    """Entry point called from ``__main__.py`` when ``--web`` is passed."""
    import uvicorn

    # Ensure web-backend diagnostic logs (auth/WS handshake) are visible even
    # without --log: the default CLI logging config installs no handlers.
    _ensure_web_logging(args)

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
