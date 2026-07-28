"""
Tests for the CreateImage tool (Wan 2.7 Image Pro text-to-image).

These tests spin up a local HTTP server (no external network access) that
plays the role of both the DashScope generation endpoint and the generated
image host. The tool's endpoint/key resolution helpers are monkeypatched to
point at the local server so the full request/parse/download/store pipeline is
exercised deterministically.
"""

import http.server
import json
import os
import socketserver
import sys
import threading
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from janito.tools.janitoweb import create_image as create_image_module
from janito.tools.janitoweb.create_image import CreateImage

# The image-serving route test needs the optional `web` extra (fastapi).
# Skip it gracefully when fastapi is not installed (e.g. minimal tox envs).
try:
    import fastapi  # noqa: F401

    _HAS_FASTAPI = True
except ModuleNotFoundError:
    _HAS_FASTAPI = False

requires_fastapi = pytest.mark.skipif(
    not _HAS_FASTAPI, reason="fastapi (web extra) is not installed"
)

PNG_BYTES = b"\x89PNG\r\n\x1a\nfakepngdata-1234567890"

# Captured request bodies (per server instance) for assertions.
_CAPTURED: dict = {}


class _Handler(http.server.BaseHTTPRequestHandler):
    """Serves the generation endpoint (POST) and the generated image (GET)."""

    def do_POST(self):  # noqa: N802 - required by BaseHTTPRequestHandler
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        _CAPTURED["last_post_path"] = self.path
        _CAPTURED["last_post_body"] = body
        _CAPTURED["last_auth"] = self.headers.get("Authorization")

        if self.path.endswith("/api/v1/services/aigc/multimodal-generation/generation"):
            base = f"http://127.0.0.1:{self.server.server_address[1]}"
            if _CAPTURED.get("fail"):
                resp = {
                    "code": "InvalidParameter",
                    "message": "Model not exist.",
                    "request_id": "req-fail-123",
                }
            else:
                resp = {
                    "output": {
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {
                                    "role": "assistant",
                                    "content": [
                                        {"image": f"{base}/img.png", "type": "image"}
                                    ],
                                },
                            }
                        ],
                        "finished": True,
                    },
                    "usage": {
                        "image_count": 1,
                        "size": "2048*2048",
                        "input_tokens": 100,
                        "output_tokens": 2,
                        "total_tokens": 102,
                    },
                    "request_id": "req-success-456",
                }
            data = json.dumps(resp).encode("utf-8")
            status = 404 if _CAPTURED.get("fail") else 200
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path == "/img.png":
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(PNG_BYTES)))
            self.end_headers()
            self.wfile.write(PNG_BYTES)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):  # silence request logging
        pass


@pytest.fixture()
def server():
    """Start a local HTTP server on an ephemeral port for a test."""
    _CAPTURED.clear()
    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture()
def patched(monkeypatch, server):
    """Point the tool's endpoint/key helpers at the local server."""
    endpoint = f"{server}/api/v1/services/aigc/multimodal-generation/generation"
    monkeypatch.setattr(create_image_module, "_generation_endpoint", lambda: endpoint)
    monkeypatch.setattr(create_image_module, "_resolve_api_key", lambda: "sk-test")
    return server


def test_success_generates_and_stores_image(patched):
    result = CreateImage().run(prompt="a red apple on a table")

    assert result["success"] is True
    assert result["content_type"] == "image"
    assert result["prompt"] == "a red apple on a table"
    assert result["request_id"] == "req-success-456"
    assert result["usage"]["image_count"] == 1

    image_path = result["image_path"]
    assert image_path.endswith(".png")
    # The file must exist and NOT be deleted.
    assert os.path.isfile(image_path)
    with open(image_path, "rb") as fh:
        assert fh.read() == PNG_BYTES

    # Verify the request that was sent.
    assert _CAPTURED["last_auth"] == "Bearer sk-test"
    sent = json.loads(_CAPTURED["last_post_body"].decode("utf-8"))
    assert sent["model"] == "wan2.7-image-pro"
    assert sent["input"]["messages"][0]["role"] == "user"
    assert sent["input"]["messages"][0]["content"] == [
        {"text": "a red apple on a table"}
    ]
    # wan2.7-image-pro text-to-image parameters.
    assert sent["parameters"]["size"] == "2K"
    assert sent["parameters"]["n"] == 1
    assert sent["parameters"]["watermark"] is False
    assert sent["parameters"]["thinking_mode"] is True

    os.remove(image_path)


def test_api_error_returns_failure(patched):
    _CAPTURED["fail"] = True
    result = CreateImage().run(prompt="anything")

    assert result["success"] is False
    assert "InvalidParameter" in result["error"]
    assert "image_path" not in result


def test_empty_prompt_rejected(monkeypatch):
    # No server/patching needed: empty prompt is rejected up front.
    result = CreateImage().run(prompt="   ")
    assert result["success"] is False
    assert "prompt" in result["error"].lower()


def test_custom_size_is_sent(patched):
    result = CreateImage().run(prompt="a mountain", size="4K")
    assert result["success"] is True
    sent = json.loads(_CAPTURED["last_post_body"].decode("utf-8"))
    assert sent["parameters"]["size"] == "4K"
    os.remove(result["image_path"])


def test_invalid_size_rejected(patched):
    result = CreateImage().run(prompt="a mountain", size="8K")
    assert result["success"] is False
    assert "size" in result["error"].lower()
    # No request should have been sent for an invalid size.
    assert "last_post_body" not in _CAPTURED


@requires_fastapi
def test_image_serving_route(tmp_path, monkeypatch):
    """The /api/images/<name> route serves only PNGs from the temp dir."""
    import tempfile

    from fastapi.testclient import TestClient

    from janito.web.backend.app import create_app
    from janito.web.backend.config import WebServerConfig

    client = TestClient(create_app(WebServerConfig()))

    tmp = tempfile.NamedTemporaryFile(
        suffix=".png", prefix="janito_image_", delete=False
    )
    tmp.write(PNG_BYTES)
    tmp.close()
    name = os.path.basename(tmp.name)

    try:
        ok = client.get(f"/api/images/{name}")
        assert ok.status_code == 200
        assert ok.headers["content-type"] == "image/png"
        assert ok.content == PNG_BYTES

        assert client.get("/api/images/missing.png").status_code == 404
        assert client.get("/api/images/notpng.txt").status_code == 400
        assert client.get("/api/images/..%2fpasswd.png").status_code in (400, 404)
    finally:
        os.remove(tmp.name)


# ── should_load() gating tests ─────────────────────────────────────────────


def test_should_load_true_when_alibaba_active(monkeypatch):
    """CreateImage.should_load() returns True when the active provider is alibaba."""
    monkeypatch.setattr(
        create_image_module,
        "_generation_endpoint",
        lambda: "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
    )
    import janito.general_config as gc

    monkeypatch.setattr(gc, "get_active_provider", lambda: "alibaba")
    assert CreateImage.should_load() is True


def test_should_load_false_when_non_alibaba_active(monkeypatch):
    """CreateImage.should_load() returns False when the active provider is not alibaba."""
    monkeypatch.setattr(
        create_image_module,
        "_generation_endpoint",
        lambda: "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
    )
    import janito.general_config as gc

    monkeypatch.setattr(gc, "get_active_provider", lambda: "openai")
    assert CreateImage.should_load() is False
    assert "not 'alibaba'" in CreateImage._load_skip_reason


def test_should_load_false_when_endpoint_missing(monkeypatch):
    """CreateImage.should_load() returns False when the endpoint cannot be resolved."""
    monkeypatch.setattr(create_image_module, "_generation_endpoint", lambda: None)
    import janito.general_config as gc

    monkeypatch.setattr(gc, "get_active_provider", lambda: "alibaba")
    assert CreateImage.should_load() is False
    assert "endpoint" in CreateImage._load_skip_reason.lower()
