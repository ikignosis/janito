"""
Tests for the HeadlessBrowse.

The tool renders a URL with headless Google Chrome and returns the page's DOM.
Tests that actually drive Chrome are skipped when no Chrome/Chromium binary is
installed on the machine (the tool itself gates on this via should_load()).

These tests spin up a local HTTP server (no external network access) to serve
static, JavaScript-rendered, and oversized payloads.
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

from janito.tools.net import headless_browse as hb_module
from janito.tools.net.headless_browse import (
    BIG_CONTENT_THRESHOLD,
    HeadlessBrowse,
    _cleanup_temp_files,
    _find_chrome,
)

CHROME = _find_chrome()
requires_chrome = pytest.mark.skipif(
    CHROME is None, reason="Google Chrome (or Chromium-based) browser not installed"
)

# Newlines are significant: Chrome preserves source newlines as text nodes, so
# the dumped DOM spans multiple lines (needed by the max_lines truncation test).
STATIC_HTML = (
    "<html><body>\n<h1>HelloJanito</h1>\n<p>static content</p>\n</body></html>"
)
# Same page but with a script that rewrites the heading -- proves JS was run.
JS_HTML = (
    "<!DOCTYPE html><html><head><title>Test</title></head>"
    '<body><h1 id="title">HelloJanito</h1><p>static content</p>'
    "<script>document.getElementById('title').textContent = 'RenderedByJS';</script>"
    "</body></html>"
)
BIG_HTML = "<html><body>" + "x" * (BIG_CONTENT_THRESHOLD + 5000) + "</body></html>"


class _Handler(http.server.BaseHTTPRequestHandler):
    """Serves /big (oversized), /js (JS-rendered) and any other path (static)."""

    def do_GET(self):  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path == "/big":
            body = BIG_HTML
        elif self.path == "/js":
            body = JS_HTML
        else:
            body = STATIC_HTML
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
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


# ── binary detection ────────────────────────────────────────────────────────


def test_find_chrome_returns_path():
    """The finder must return a path to an existing browser binary or None."""
    chrome = _find_chrome()
    if chrome is None:
        pytest.skip("No Chrome binary installed")
    assert os.path.isfile(chrome)


def test_should_load_matches_binary_presence():
    """should_load() must agree with the binary finder and cache the path."""
    found = _find_chrome() is not None
    assert HeadlessBrowse.should_load() is found
    if found:
        assert HeadlessBrowse._chrome_binary == _find_chrome()
        assert HeadlessBrowse._load_skip_reason == ""
    else:
        assert "not found" in HeadlessBrowse._load_skip_reason


# ── URL validation (no Chrome needed) ───────────────────────────────────────


def test_invalid_url_rejected():
    """Non-http(s) URLs must be rejected before launching Chrome."""
    tool = HeadlessBrowse()
    result = tool.run(url="not a url")

    assert result["success"] is False
    assert "http:// or https://" in result["error"]


# ── rendering (requires Chrome) ─────────────────────────────────────────────


@requires_chrome
def test_renders_static_page(server):
    """Browsing a static page must return the page's DOM content."""
    tool = HeadlessBrowse()
    result = tool.run(url=f"{server}/static")

    assert result["success"] is True
    assert "HelloJanito" in result["content"]
    assert result["url"] == f"{server}/static"
    assert result["chrome"] == CHROME
    assert result["headless_mode"] in ("new", "legacy")
    assert result["exit_code"] == 0
    assert result["content_length"] > 0
    assert "tmp_filename" not in result


@requires_chrome
def test_renders_javascript(server):
    """JavaScript must be executed before the DOM is dumped."""
    tool = HeadlessBrowse()
    result = tool.run(url=f"{server}/js", wait_ms=2000)

    assert result["success"] is True
    assert "RenderedByJS" in result["content"]
    assert "HelloJanito" not in result["content"]


@requires_chrome
def test_max_length_truncation(server):
    """Content above max_length must be truncated with the marker."""
    tool = HeadlessBrowse()
    result = tool.run(url=f"{server}/static", max_length=50)

    assert result["success"] is True
    assert result["content"].endswith("... [truncated]")
    assert len(result["content"]) <= 50 + len("... [truncated]")


@requires_chrome
def test_max_lines_truncation(server):
    """Content above max_lines must be truncated to that many lines."""
    tool = HeadlessBrowse()
    result = tool.run(url=f"{server}/static", max_length=None, max_lines=2)

    assert result["success"] is True
    assert "truncated" in result["content"]
    assert len(result["content"].split("\n")) <= 3  # 2 lines + marker


@requires_chrome
def test_big_content_stored_to_temp_file(server):
    """Oversized DOM must be written to a temp file and reported via message."""
    tool = HeadlessBrowse()
    result = tool.run(url=f"{server}/big")

    assert result["success"] is True
    assert result.get("too_big") is True

    tmp_filename = result["tmp_filename"]
    assert os.path.isfile(tmp_filename)

    # Chrome normalises the DOM (adds <head>, trailing newline, ...), so we
    # assert on the oversized payload rather than byte-equality.
    with open(tmp_filename, encoding="utf-8") as fh:
        stored = fh.read()
    assert len(stored) > BIG_CONTENT_THRESHOLD
    assert "x" * BIG_CONTENT_THRESHOLD in stored

    assert tmp_filename in result["message"]
    assert "content" not in result
    assert tmp_filename in hb_module._TEMP_FILES


@requires_chrome
def test_threshold_none_disables_temp_file(server):
    """threshold=None disables the temp-file behaviour (limits still apply)."""
    tool = HeadlessBrowse()
    result = tool.run(url=f"{server}/big", threshold=None, max_length=100)

    assert result["success"] is True
    assert result.get("too_big") is None
    assert "content" in result
    assert result["content"].endswith("... [truncated]")
    assert "tmp_filename" not in result


@requires_chrome
def test_cleanup_removes_temp_files(server):
    """_cleanup_temp_files() must delete every tracked temp file."""
    tool = HeadlessBrowse()
    result = tool.run(url=f"{server}/big")
    tmp_filename = result["tmp_filename"]

    assert os.path.isfile(tmp_filename)
    _cleanup_temp_files()
    assert not os.path.exists(tmp_filename)
    assert tmp_filename not in hb_module._TEMP_FILES


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
