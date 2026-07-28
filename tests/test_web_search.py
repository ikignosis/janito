"""
Tests for the WebSearch tool (Brave Search API).

These tests spin up a local HTTP server (no external network access) that
plays the role of the Brave Search endpoint. The tool's base URL and API-key
resolver are monkeypatched to point at the local server so the full
request/parse pipeline is exercised deterministically.
"""

import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from janito.tools.net import web_search as web_search_module
from janito.tools.net.web_search import WebSearch

# Captured request details (per server instance) for assertions.
_CAPTURED: dict = {}


def _sample_response() -> dict:
    """A minimal but representative Brave Search API response."""
    return {
        "type": "search",
        "query": {"original": "python asyncio", "altered": None},
        "web": {
            "type": "search",
            "results": [
                {
                    "title": "asyncio — Asynchronous I/O",
                    "url": "https://docs.python.org/3/library/asyncio.html",
                    "description": "This module provides infrastructure for "
                    "writing single-threaded concurrent code.",
                    "age": "2 days ago",
                    "language": "en",
                    "family_friendly": True,
                },
                {
                    "title": "Real Python: Async IO",
                    "url": "https://realpython.com/async-io-python/",
                    "description": "A complete walkthrough of async IO in Python.",
                    "age": "1 month ago",
                    "language": "en",
                },
            ],
        },
        "news": {
            "type": "news",
            "results": [
                {
                    "title": "Python 3.13 released",
                    "url": "https://example.com/news/py313",
                    "description": "The latest Python is out.",
                    "source": "Example News",
                    "age": "3 hours ago",
                }
            ],
        },
    }


class _Handler(http.server.BaseHTTPRequestHandler):
    """Serves the Brave web-search endpoint (GET /res/v1/web/search)."""

    def do_GET(self):  # noqa: N802 - required by BaseHTTPRequestHandler
        _CAPTURED["last_path"] = self.path
        _CAPTURED["last_token"] = self.headers.get("X-Subscription-Token")
        _CAPTURED["last_accept"] = self.headers.get("Accept")

        if _CAPTURED.get("fail"):
            resp = {
                "type": "ErrorResponse",
                "error": {
                    "id": "err-1",
                    "status": 422,
                    "code": "VALIDATION_FAILED",
                    "detail": "q parameter is required",
                },
            }
            data = json.dumps(resp).encode("utf-8")
            self.send_response(422)
        else:
            data = json.dumps(_sample_response()).encode("utf-8")
            self.send_response(200)

        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # silence request logging
        pass


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


@pytest.fixture
def brave_server(monkeypatch):
    """Start a local fake Brave endpoint and point the tool at it."""
    _CAPTURED.clear()
    server = _Server(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    monkeypatch.setattr(
        web_search_module, "_BRAVE_BASE_URL", f"http://127.0.0.1:{port}/res"
    )
    monkeypatch.setattr(web_search_module, "_resolve_api_key", lambda: "test-token")

    yield server

    server.shutdown()
    server.server_close()


def test_should_load_without_key(monkeypatch):
    """should_load() must be False when no API key is configured."""
    monkeypatch.setattr(web_search_module, "_resolve_api_key", lambda: None)
    assert WebSearch.should_load() is False
    assert "brave_api_key" in WebSearch._load_skip_reason


def test_should_load_with_key(monkeypatch):
    """should_load() must be True when an API key is configured."""
    monkeypatch.setattr(web_search_module, "_resolve_api_key", lambda: "abc")
    assert WebSearch.should_load() is True


def test_successful_search(brave_server):
    """A successful search returns parsed web + news results."""
    result = WebSearch().run(query="python asyncio")

    assert result["success"] is True
    assert result["query"] == "python asyncio"
    assert result["result_count"] == 2
    assert len(result["results"]) == 2
    assert result["results"][0]["title"] == "asyncio — Asynchronous I/O"
    assert result["results"][0]["url"].endswith("asyncio.html")
    assert len(result["news"]) == 1
    assert result["news"][0]["source"] == "Example News"
    assert "execution_time_ms" in result


def test_request_sends_token_and_params(brave_server):
    """The request must carry the subscription token and query params."""
    WebSearch().run(query="hello world", count=5, country="US", safesearch="strict")

    assert _CAPTURED["last_token"] == "test-token"
    assert _CAPTURED["last_accept"] == "application/json"
    path = _CAPTURED["last_path"]
    assert path.startswith("/res/v1/web/search?")
    assert "q=hello+world" in path
    assert "count=5" in path
    assert "country=US" in path
    assert "safesearch=strict" in path


def test_empty_query_rejected(brave_server):
    """An empty query returns an error without hitting the network."""
    result = WebSearch().run(query="   ")
    assert result["success"] is False
    assert "query" in result["error"].lower()


def test_invalid_safesearch_rejected(brave_server):
    """An invalid safesearch value returns an error."""
    result = WebSearch().run(query="test", safesearch="banana")
    assert result["success"] is False
    assert "safesearch" in result["error"].lower()


def test_count_is_clamped(brave_server):
    """count is clamped to the 1-20 range accepted by the API."""
    WebSearch().run(query="test", count=999)
    assert "count=20" in _CAPTURED["last_path"]

    WebSearch().run(query="test", count=-3)
    assert "count=1" in _CAPTURED["last_path"]


def test_http_error_handled(brave_server):
    """An HTTP error response is surfaced as success=False with the detail."""
    _CAPTURED["fail"] = True
    result = WebSearch().run(query="test")

    assert result["success"] is False
    assert result.get("status_code") == 422
    assert "422" in result["error"]


def test_missing_api_key_at_runtime(monkeypatch):
    """If the key disappears at runtime, run() returns a clear error."""
    monkeypatch.setattr(web_search_module, "_resolve_api_key", lambda: None)
    result = WebSearch().run(query="test")
    assert result["success"] is False
    assert "brave_api_key" in result["error"]


def test_html_decoration_is_cleaned():
    """Highlighting tags and HTML entities are stripped from snippets."""
    data = {
        "web": {
            "results": [
                {
                    "title": "A &amp; B &lt;tag&gt;",
                    "url": "https://x.com",
                    "description": "A &quot;<strong>Hello</strong>, world&quot; "
                    "program &#x27;demo&#x27; &amp; more.",
                }
            ]
        }
    }
    results = web_search_module._extract_web_results(data)
    assert results[0]["title"] == "A & B <tag>"
    assert results[0]["description"] == "A \"Hello, world\" program 'demo' & more."
    assert "<strong>" not in results[0]["description"]
    assert "&quot;" not in results[0]["description"]
