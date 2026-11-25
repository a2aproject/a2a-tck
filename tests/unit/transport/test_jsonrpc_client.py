"""Regression tests for the JSON-RPC transport client (issue #263).

``httpx.Client(base_url=...)`` normalizes the base URL's path to end with a
trailing slash, so posting to ``"/"`` requests ``<interface URL>/`` rather than
the interface URL declared in the Agent Card.  An agent or gateway that routes
the declared URL exactly answers 404 before the agent sees the request.  The
client must post to the exact interface URL.
"""

from __future__ import annotations

import json
import threading

from http.server import BaseHTTPRequestHandler, HTTPServer

from tck.transport.jsonrpc_client import JsonRpcClient


class _PathRecordingHandler(BaseHTTPRequestHandler):
    """Records request paths and answers a minimal JSON-RPC or SSE response."""

    paths: list[str] = []
    streaming = False

    def do_POST(self) -> None:
        type(self).paths.append(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length:
            self.rfile.read(content_length)
        if type(self).streaming:
            body = b'data: {"jsonrpc": "2.0", "id": 1, "result": {}}\n\n'
            content_type = "text/event-stream"
        else:
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {}}).encode()
            content_type = "application/json"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Silence the default stderr access log."""


def _serve(streaming: bool) -> tuple[HTTPServer, str]:
    handler = type("Handler", (_PathRecordingHandler,), {"paths": [], "streaming": streaming})
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}/a2a/my-agent"


def test_send_message_posts_to_exact_interface_url() -> None:
    """A unary JSON-RPC call targets the interface URL without a trailing slash."""
    server, url = _serve(streaming=False)
    try:
        client = JsonRpcClient(url)
        response = client.send_message({"role": "user", "parts": [{"kind": "text", "text": "hi"}]})
        client.close()
        assert response.success
        assert server.RequestHandlerClass.paths == ["/a2a/my-agent"]
    finally:
        server.shutdown()


def test_send_streaming_message_posts_to_exact_interface_url() -> None:
    """A streaming JSON-RPC call targets the interface URL without a trailing slash."""
    server, url = _serve(streaming=True)
    try:
        client = JsonRpcClient(url)
        response = client.send_streaming_message({"role": "user", "parts": [{"kind": "text", "text": "hi"}]})
        for _ in response.events:
            pass
        client.close()
        assert server.RequestHandlerClass.paths == ["/a2a/my-agent"]
    finally:
        server.shutdown()
