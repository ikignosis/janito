"""FastAPI application factory + ``run_web(args)`` entry point.

At the point ``run_web`` is called, ``__main__.py`` has already:
  - configured logging
  - set ``running_privileges`` from -r -w -x
  - validated the runtime config (API key / endpoint / model)
"""

import json
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import WebServerConfig
from .security import TokenAuthMiddleware, add_cors
from .session import SessionManager

logger = logging.getLogger(__name__)


def create_app(config: WebServerConfig) -> FastAPI:
    """Build the FastAPI application."""
    from .routers import chat as chat_router
    from .routers import config as config_router
    from .routers import images as images_router
    from .routers import mcp as mcp_router
    from .routers import tools as tools_router

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
    app.include_router(images_router.router, prefix="/api/images", tags=["images"])

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
            _token_script = (
                "<script>window.__JANITO_TOKEN__ = "
                + json.dumps(config.auth_token)
                + ";</script>"
            )

            @app.get("/", response_class=HTMLResponse, include_in_schema=False)
            async def serve_index():
                # Read the file per request so frontend edits apply without
                # restarting the server, and send ``no-store`` so browsers
                # never serve a stale shell. (JS/CSS assets remain cacheable
                # and are invalidated with ?v=N query strings instead.)
                html = index_file.read_text(encoding="utf-8")
                return HTMLResponse(
                    html.replace("</head>", _token_script + "\n</head>", 1),
                    headers={"Cache-Control": "no-store"},
                )

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
        handler.setFormatter(logging.Formatter("%(levelname)s: %(name)s: %(message)s"))
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

    url = f"http://{config.web_host}:{config.web_port}"

    if not config.no_web_open:
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
    print(f"  Model: {config.model or '?'}")
    if config.auth_token:
        print("  Auth: bearer token required (JANITO_WEB_TOKEN is set)")
    print("  Press Ctrl+C to stop.")

    try:
        uvicorn.run(
            app, host=config.web_host, port=config.web_port, log_level="warning"
        )
    finally:
        from janito.mcp_manager import shutdown_mcp_manager

        try:
            shutdown_mcp_manager()
        except Exception:
            pass
