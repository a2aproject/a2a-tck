"""Regression tests for the HTTP+JSON transport client (issue #225).

A conformant server may answer a streamed ``message:stream`` request with a
non-2xx status and a JSON error body.  ``_request_streaming`` opens the response
with ``stream=True`` and, on an error status, must make the body readable before
closing it; otherwise ``_extract_error`` (reached via ``.error``) calls
``.json()``/``.text`` on an unread streamed response and raises
``httpx.ResponseNotRead`` (a ``StreamError``/``RuntimeError`` subclass) that the
harness does not expect, crashing HTTP_JSON-SSE-001 instead of skipping.
"""

from __future__ import annotations

import json
import threading

from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Iterator

import httpx
import pytest

from tck.transport.http_json_client import HttpJsonClient, _extract_error


_ERROR_MESSAGE = "task not found"
_ERROR_BODY = json.dumps({"error": {"code": 404, "message": _ERROR_MESSAGE}}).encode()
_STATUS_BAD_REQUEST = 400


class _ErrorHandler(BaseHTTPRequestHandler):
    """Returns 400 with an AIP-193 JSON error body to any streamed POST."""

    def do_POST(self) -> None:
        # Drain the request body before responding; leaving it unread makes some
        # platforms (notably Windows) reset the connection, which would surface
        # as a spurious httpx.ReadError rather than the 400 under test.
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length:
            self.rfile.read(content_length)
        self.send_response(_STATUS_BAD_REQUEST)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(_ERROR_BODY)))
        self.end_headers()
        self.wfile.write(_ERROR_BODY)

    def log_message(self, format: str, *args: Any) -> None:
        pass


@pytest.fixture
def error_server() -> Iterator[str]:
    """A stdlib HTTP server that answers every POST with a 400 JSON error."""
    server = HTTPServer(("127.0.0.1", 0), _ErrorHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


def test_streaming_error_does_not_crash_and_returns_message(error_server: str) -> None:
    """Streaming to a server that returns 400 must yield the error string, not raise.

    This is the exact scenario from issue #225: without reading the streamed
    body before close, ``.error`` raised ``httpx.ResponseNotRead``.
    """
    client = HttpJsonClient(error_server)
    try:
        response = client.send_streaming_message(message={"role": "user", "parts": []})
        assert response.success is False
        assert response.status_code == _STATUS_BAD_REQUEST
        # ``.error`` routes through ``_extract_error`` on the closed streamed
        # response; it must return the server's error string, not raise.
        error = response.error
        assert error is not None
        assert "[400]" in error
        assert _ERROR_MESSAGE in error
    finally:
        client.close()


def test_extract_error_on_read_streamed_response(error_server: str) -> None:
    """Suite-level path: ``_extract_error`` on a read+closed streamed response returns a string."""
    with httpx.Client(base_url=error_server) as raw:
        request = raw.build_request("POST", "/message:stream", json={})
        response = raw.send(request, stream=True)
        try:
            assert response.status_code == _STATUS_BAD_REQUEST
            response.read()  # what _request_streaming now does before close()
        finally:
            response.close()
        result = _extract_error(response)
    assert isinstance(result, str)
    assert "[400]" in result
    assert _ERROR_MESSAGE in result
