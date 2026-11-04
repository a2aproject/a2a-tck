"""Regression tests for the JSON-RPC transport client (issue #263).

The JSON-RPC client must POST to the Agent Card interface URL exactly as
declared.  Posting ``"/"`` relative to an ``httpx`` ``base_url`` appends a
trailing slash to a path-bearing URL (``/a2a`` becomes ``/a2a/``), so an agent
that routes the declared URL exactly answers 404.
"""

from __future__ import annotations

import json
import threading

from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Iterator

import pytest

from tck.transport.jsonrpc_client import JsonRpcClient


_BODY = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {}}).encode()


class _RecordingHandler(BaseHTTPRequestHandler):
    """Records each POST path and answers with an empty JSON-RPC result."""

    paths: list[str] = []

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length:
            self.rfile.read(content_length)
        self.paths.append(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(_BODY)))
        self.end_headers()
        self.wfile.write(_BODY)

    def log_message(self, format: str, *args: Any) -> None:
        pass


@pytest.fixture
def recording_server() -> Iterator[tuple[str, list[str]]]:
    """A stdlib HTTP server that records the path of every POST."""
    paths: list[str] = []
    handler = type("_Handler", (_RecordingHandler,), {"paths": paths})
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", paths
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize("path", ["/a2a/my-agent", "/a2a/my-agent/", "/"])
def test_requests_go_to_exact_interface_url(recording_server: tuple[str, list[str]], path: str) -> None:
    """Unary and streaming calls must POST to the interface URL path unchanged."""
    base, paths = recording_server
    client = JsonRpcClient(f"{base}{path}")
    try:
        assert client.send_message(message={"role": "user", "parts": []}).success is True
        assert client.send_streaming_message(message={"role": "user", "parts": []}).success is True
    finally:
        client.close()
    assert paths == [path, path]
