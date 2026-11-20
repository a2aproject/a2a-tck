"""Raw compatibility probes use the selected interface URL like regular operations (#262)."""

from __future__ import annotations

import threading

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Iterator

import pytest

from tck.transport._helpers import A2A_VERSION_HEADER
from tck.transport.http_json_client import HttpJsonClient
from tck.transport.jsonrpc_client import JsonRpcClient


class _RecordingHandler(BaseHTTPRequestHandler):
    requests: list[tuple[str, str | None]] = []

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        type(self).requests.append((self.path, self.headers.get(A2A_VERSION_HEADER)))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args: object) -> None:
        pass


@contextmanager
def _running_server() -> Iterator[str]:
    _RecordingHandler.requests = []
    server = HTTPServer(("127.0.0.1", 0), _RecordingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize(
    ("suffix", "expected"),
    [
        ("", "/message:send"),
        ("/", "/message:send"),
        ("/agents/a/rest", "/agents/a/rest/message:send"),
        ("/agents/a/rest/", "/agents/a/rest/message:send"),
    ],
)
def test_http_json_raw_request_joins_the_interface_url(suffix: str, expected: str) -> None:
    """Keep the interface path prefix and add exactly one slash."""
    with _running_server() as origin:
        client = HttpJsonClient(origin + suffix)
        try:
            client.raw_request("POST", "/message:send", json={})
        finally:
            client.close()
    assert [path for path, _ in _RecordingHandler.requests] == [expected]


@pytest.mark.parametrize(
    ("suffix", "expected"),
    [("", "/"), ("/agents/a/rpc", "/agents/a/rpc/")],
)
def test_jsonrpc_raw_request_posts_to_the_regular_endpoint(suffix: str, expected: str) -> None:
    """Send raw JSON-RPC probes to the endpoint regular calls use."""
    with _running_server() as origin:
        client = JsonRpcClient(origin + suffix)
        try:
            client.raw_request("POST", json={"jsonrpc": "2.0", "id": 1, "method": "SendMessage", "params": {}})
            client.send_message(message={"role": "ROLE_USER", "parts": [{"text": "x"}], "messageId": "m"})
        finally:
            client.close()
    raw_path, typed_path = (path for path, _ in _RecordingHandler.requests)
    assert raw_path == typed_path == expected


def test_raw_request_headers_override_the_session_defaults() -> None:
    """Let a probe replace a default header such as A2A-Version."""
    with _running_server() as origin:
        client = HttpJsonClient(origin)
        try:
            client.raw_request("POST", "/message:send", json={}, headers={A2A_VERSION_HEADER: "99.0"})
        finally:
            client.close()
    assert _RecordingHandler.requests == [("/message:send", "99.0")]
