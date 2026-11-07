"""Regression tests for the JSON-RPC transport client (issue #242).

The A2A JSON representation for ``GetTask`` params requires ``historyLength``
(camelCase). ``JsonRpcClient.get_task()`` accepts a Pythonic ``history_length``
keyword argument, but must serialize it onto the wire as ``historyLength`` —
sending the raw Python parameter name causes conformant servers to silently
ignore the client's requested history limit.
"""

from __future__ import annotations

import json
import threading

from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Iterator

import pytest

from tck.transport.jsonrpc_client import JsonRpcClient


_RESULT_BODY = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"id": "task-1"}}).encode()


class _RecordingHandler(BaseHTTPRequestHandler):
    """Records the JSON-RPC request's ``params`` and returns a canned success response."""

    captured_params: dict[str, Any] | None = None

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b""
        payload = json.loads(body)
        _RecordingHandler.captured_params = payload["params"]
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(_RESULT_BODY)))
        self.end_headers()
        self.wfile.write(_RESULT_BODY)

    def log_message(self, format: str, *args: Any) -> None:
        pass


@pytest.fixture
def recording_server() -> Iterator[str]:
    """A stdlib HTTP server that records the JSON-RPC request body it receives."""
    _RecordingHandler.captured_params = None
    server = HTTPServer(("127.0.0.1", 0), _RecordingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


def test_get_task_sends_history_length_as_camel_case(recording_server: str) -> None:
    """Regression test for issue #242.

    ``get_task(history_length=1)`` must produce JSON-RPC params containing
    ``{"id": ..., "historyLength": 1}``, not ``history_length``.
    """
    client = JsonRpcClient(recording_server)
    try:
        client.get_task(id="task-1", history_length=1)
    finally:
        client.close()

    params = _RecordingHandler.captured_params
    assert params == {"id": "task-1", "historyLength": 1}
