"""
Tests for the MCP client transports and the MCP manager
(:mod:`janito.mcp_client` and :mod:`janito.mcp_manager`).

Covers the three bugs fixed around the transports:

- stdio commands configured as a single string (e.g. by ``/mcp add``) are
  split with ``shlex`` so ``subprocess.Popen`` receives proper argv;
- ``MCPManager.get_all_tools`` reconnects a dead service *and* still lists
  its tools (previously the reconnect path skipped listing entirely);
- the HTTP transport clears its connected flag when a request fails, so
  callers can detect the loss and reconnect.

Each test spins up a tiny fake MCP server (stdio subprocess or HTTP/SSE
thread) and drives the real transport code end to end.
"""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.config_dir as config_dir_mod
from janito.mcp_client import HttpTransport, StdioTransport, create_transport
from janito.mcp_config import add_service, remove_service
from janito.mcp_manager import MCPManager

# ---------------------------------------------------------------------------
# Fake stdio MCP server (written to a temp file, then spawned as a subprocess)
# ---------------------------------------------------------------------------

FAKE_STDIO_SERVER = """
import json
import sys


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = msg.get("method")
        msg_id = msg.get("id")

        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake", "version": "1.0.0"},
            }
        elif method in ("initialized", "notifications/initialized"):
            continue
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "echo",
                        "description": "Echo a message back",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"message": {"type": "string"}},
                            "required": ["message"],
                        },
                    },
                    {
                        "name": "add",
                        "description": "Add two numbers",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "a": {"type": "number"},
                                "b": {"type": "number"},
                            },
                            "required": ["a", "b"],
                        },
                    },
                ]
            }
        elif method == "tools/call":
            params = msg.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})
            if name == "echo":
                text = "echo: %s" % args.get("message", "")
            elif name == "add":
                text = "sum: %s" % (args.get("a", 0) + args.get("b", 0))
            else:
                text = "unknown: %s" % name
            result = {"content": [{"type": "text", "text": text}]}
        else:
            result = {}

        if msg_id is not None:
            sys.stdout.write(
                json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}) + "\\n"
            )
            sys.stdout.flush()


if __name__ == "__main__":
    main()
"""


def _write_fake_stdio_server(tmp_path) -> str:
    """Write the fake stdio server to ``tmp_path`` and return its path."""
    server_path = tmp_path / "fake_mcp_server.py"
    server_path.write_text(FAKE_STDIO_SERVER, encoding="utf-8")
    return str(server_path)


# ---------------------------------------------------------------------------
# Fake HTTP/SSE MCP server (served from a background thread)
# ---------------------------------------------------------------------------


class _FakeHttpMCPHandler(BaseHTTPRequestHandler):
    """Answers JSON-RPC POSTs with SSE ``data: {...}`` frames."""

    def do_POST(self):  # noqa: N802 (BaseHTTPRequestHandler API)
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")

        method = body.get("method")
        msg_id = body.get("id")

        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake-http", "version": "1.0.0"},
            }
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "ping",
                        "description": "Ping the server",
                        "inputSchema": {"type": "object", "properties": {}},
                    }
                ]
            }
        elif method == "tools/call":
            args = body.get("params", {}).get("arguments", {})
            result = {"content": [{"type": "text", "text": f"pong:{args}"}]}
        else:
            result = {}

        response = {"jsonrpc": "2.0", "id": msg_id, "result": result}
        payload = f"data: {json.dumps(response)}\n\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # silence request logging
        pass


@pytest.fixture
def _isolate(tmp_path, monkeypatch):
    """Point the config dir at a temp dir so mcp_services.json stays hermetic."""
    monkeypatch.setattr(config_dir_mod, "_config_dir", tmp_path)
    yield


# ---------------------------------------------------------------------------
# stdio transport
# ---------------------------------------------------------------------------


def test_create_transport_splits_stdio_command():
    """A string command is split with shlex so Popen gets proper argv."""
    config = {
        "transport": "stdio",
        "command": "python -m mcp.server --port 5000",
    }
    transport = create_transport(config)
    assert isinstance(transport, StdioTransport)
    assert transport.command == ["python", "-m", "mcp.server", "--port", "5000"]


def test_create_transport_keeps_pre_split_list_command():
    """A command already given as an argv list is used as-is."""
    config = {"transport": "stdio", "command": ["python", "/tmp/x.py"]}
    transport = create_transport(config)
    assert isinstance(transport, StdioTransport)
    assert transport.command == ["python", "/tmp/x.py"]


def test_stdio_transport_end_to_end(tmp_path):
    """Connect, list tools and call tools through a real stdio subprocess."""
    server = _write_fake_stdio_server(tmp_path)
    transport = create_transport(
        {"transport": "stdio", "command": f"{sys.executable} {server}"}
    )

    assert transport.connect()
    try:
        tools = transport.list_tools()
        assert {t["name"] for t in tools} == {"echo", "add"}

        result = transport.call_tool("echo", {"message": "hello"})
        assert result["content"][0]["text"] == "echo: hello"

        result = transport.call_tool("add", {"a": 2, "b": 3})
        assert result["content"][0]["text"] == "sum: 5"
    finally:
        transport.disconnect()

    assert not transport.is_connected


# ---------------------------------------------------------------------------
# MCPManager
# ---------------------------------------------------------------------------


def test_mcp_manager_loads_and_routes_tools(tmp_path, _isolate):
    """The manager connects a service, prefixes its tools and routes calls."""
    server = _write_fake_stdio_server(tmp_path)
    command = f"{sys.executable} {server}"

    add_service("loc", {"transport": "stdio", "command": command})
    try:
        manager = MCPManager()
        manager.load_services(["loc"])

        names = [t["function"]["name"] for t in manager.get_all_tools()]
        assert names == ["loc_echo", "loc_add"]

        # call_tool goes through the cached tool names, no re-listing needed
        result = manager.call_tool("loc_add", {"a": 2, "b": 3})
        assert result == "sum: 5"
    finally:
        manager.shutdown()
        remove_service("loc")


def test_mcp_manager_reconnect_keeps_tools(tmp_path, _isolate):
    """Killing a service must not silently drop its tools on reconnect."""
    server = _write_fake_stdio_server(tmp_path)
    command = f"{sys.executable} {server}"

    add_service("loc", {"transport": "stdio", "command": command})
    manager = MCPManager()
    try:
        manager.load_services(["loc"])
        names = [t["function"]["name"] for t in manager.get_all_tools()]
        assert names == ["loc_echo", "loc_add"]

        # Kill the server subprocess
        client = manager._clients["loc"]
        client.process.terminate()
        client.process.wait()
        assert not client.is_connected

        # A forced refresh reconnects AND still lists the service's tools
        names_after = [
            t["function"]["name"] for t in manager.get_all_tools(force_refresh=True)
        ]
        assert names_after == ["loc_echo", "loc_add"]
    finally:
        manager.shutdown()
        remove_service("loc")


# ---------------------------------------------------------------------------
# HTTP transport
# ---------------------------------------------------------------------------


def test_http_transport_connects_and_lists_tools():
    """The HTTP transport works against an SSE-style endpoint."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeHttpMCPHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}"

    transport = HttpTransport(url)
    try:
        assert transport.connect()
        assert transport.is_connected

        tools = transport.list_tools()
        assert {t["name"] for t in tools} == {"ping"}

        result = transport.call_tool("ping", {})
        assert result["content"][0]["text"].startswith("pong")
    finally:
        transport.disconnect()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_http_transport_marks_disconnected_on_failure():
    """A failed request clears the connected flag so callers can reconnect."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeHttpMCPHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}"

    transport = HttpTransport(url)
    try:
        assert transport.connect()
        assert transport.is_connected
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    # Server is gone: the request fails and the transport must know it
    with pytest.raises(Exception):
        transport.send_request("tools/list")
    assert not transport.is_connected
