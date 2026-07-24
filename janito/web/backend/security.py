"""Security middleware for the web backend.

- Localhost-only by default (the server binds to 127.0.0.1 unless --host is set).
- Optional bearer-token auth via the ``JANITO_WEB_TOKEN`` env var.
- CORS middleware for development.
"""

import logging
from typing import Optional
from urllib.parse import parse_qs

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def add_cors(app: FastAPI) -> None:
    """Add permissive CORS middleware (for dev / same-machine usage)."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class TokenAuthMiddleware:
    """Optional bearer-token authentication.

    Enabled only when ``auth_token`` is not None. Requests without a matching
    ``Authorization: Bearer <token>`` header (or ``?token=`` query param for
    WebSockets) receive a 401 response.

    The root path and static assets are always allowed so the login-less UI
    can load; API routes under ``/api`` are protected.
    """

    def __init__(self, app, auth_token: Optional[str]):
        self.app = app
        self.auth_token = auth_token

    async def __call__(self, scope, receive, send):
        if self.auth_token is None:
            await self.app(scope, receive, send)
            return

        if scope["type"] == "http":
            request = Request(scope, receive)
            path = request.url.path
            # Always allow non-API paths (frontend assets, docs)
            if not path.startswith("/api"):
                await self.app(scope, receive, send)
                return
            if self._authorized(request.headers.get("authorization"),
                                request.query_params.get("token")):
                await self.app(scope, receive, send)
                return
            logger.warning("[auth] HTTP 401 Unauthorized: %s %s",
                           request.method, path)
            response = JSONResponse(
                {"detail": "Unauthorized"}, status_code=401
            )
            await response(scope, receive, send)

        elif scope["type"] == "websocket":
            # For WebSockets, check the token query param during handshake.
            # The client sends it URL-encoded (encodeURIComponent), so decode
            # it with parse_qs before comparing.
            path = scope.get("path", "")
            query_string = scope.get("query_string", b"").decode()
            token = None
            params = parse_qs(query_string)
            if "token" in params:
                token = params["token"][0]
            logger.warning(
                "[auth] WS handshake path=%s token_present=%s token_match=%s",
                path, token is not None, token == self.auth_token,
            )
            if token == self.auth_token:
                await self.app(scope, receive, send)
                return
            # Reject the handshake
            logger.warning("[auth] WS handshake REJECTED (1008) for %s", path)
            close_message = {"type": "websocket.close", "code": 1008}
            await send(close_message)
        else:
            await self.app(scope, receive, send)

    def _authorized(self, auth_header: Optional[str],
                    query_token: Optional[str]) -> bool:
        if query_token and query_token == self.auth_token:
            return True
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[len("Bearer "):] == self.auth_token
        return False
