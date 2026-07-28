"""
Tests for the GetUrl tool's oversized-content handling.

When fetched content exceeds a threshold (default 10k characters), the tool
stores the full content in a temporary file and returns a pointer message
instead of the (huge) inline payload. The temporary files are tracked and
removed when the janito process exits.

These tests spin up a local HTTP server (no external network access) to serve
both small and oversized payloads.
"""

import http.server
import socketserver
import sys
import threading
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import os

import pytest

from janito.tools.net import get_url as get_url_module
from janito.tools.net.get_url import BIG_CONTENT_THRESHOLD, GetUrl, _cleanup_temp_files

SMALL_PAYLOAD = "hello small world"
BIG_PAYLOAD = "x" * (BIG_CONTENT_THRESHOLD + 5000)  # clearly over the threshold


class _Handler(http.server.BaseHTTPRequestHandler):
    """Serves /big (oversized) and any other path (small)."""

    def do_GET(self):  # noqa: N802 - required by BaseHTTPRequestHandler
        body = BIG_PAYLOAD if self.path == "/big" else SMALL_PAYLOAD
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # silence request logging
        pass


@pytest.fixture()
def server():
    """Start a local HTTP server on an ephemeral port for the duration of a test."""
    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture(autouse=True)
def _clean_temp_registry():
    """Ensure no tracked temp files leak between tests."""
    yield
    _cleanup_temp_files()


def test_big_content_stored_to_temp_file(server):
    """Oversized content must be written to a temp file and reported via message."""
    tool = GetUrl()
    result = tool.run(url=f"{server}/big")

    assert result["success"] is True
    assert result.get("too_big") is True

    tmp_filename = result["tmp_filename"]
    assert os.path.isfile(tmp_filename)

    # The stored file must contain the full oversized payload.
    with open(tmp_filename, encoding="utf-8") as fh:
        assert fh.read() == BIG_PAYLOAD

    # The returned message must point to the temp file, and there must be no
    # inline content payload.
    assert tmp_filename in result["message"]
    assert "Content was too big, stored at" in result["message"]
    assert "content" not in result

    # The file must have been registered for cleanup on exit.
    assert tmp_filename in get_url_module._TEMP_FILES


def test_small_content_returned_inline(server):
    """Content below the threshold is returned inline as before."""
    tool = GetUrl()
    result = tool.run(url=f"{server}/small")

    assert result["success"] is True
    assert result.get("too_big") is None
    assert result.get("content") == SMALL_PAYLOAD
    assert "tmp_filename" not in result


def test_threshold_none_disables_temp_file(server):
    """Passing threshold=None disables the temp-file behaviour (limits still apply)."""
    tool = GetUrl()
    # With no threshold but a max_length, big content is truncated inline.
    result = tool.run(url=f"{server}/big", threshold=None, max_length=100)

    assert result["success"] is True
    assert result.get("too_big") is None
    assert "content" in result
    assert result["content"].endswith("... [truncated]")
    assert "tmp_filename" not in result


def test_cleanup_removes_temp_files(server):
    """_cleanup_temp_files() must delete every tracked temp file."""
    tool = GetUrl()
    result = tool.run(url=f"{server}/big")
    tmp_filename = result["tmp_filename"]

    assert os.path.isfile(tmp_filename)
    _cleanup_temp_files()
    assert not os.path.exists(tmp_filename)
    assert tmp_filename not in get_url_module._TEMP_FILES


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
