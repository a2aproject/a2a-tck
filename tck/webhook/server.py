"""Lightweight HTTP server that captures incoming webhook requests.

Used by push notification delivery tests (PUSH-DELIVER-*) to verify
that the SUT sends webhook payloads when a task state changes.
"""

from __future__ import annotations

import contextlib
import json
import threading

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


@dataclass
class WebhookRequest:
    """A captured webhook request."""

    method: str
    path: str
    headers: dict[str, str]
    body: bytes
    json_body: Any = None

    def __post_init__(self) -> None:  # noqa: D105
        if self.json_body is None and self.body:
            with contextlib.suppress(json.JSONDecodeError, UnicodeDecodeError):
                self.json_body = json.loads(self.body)


@dataclass
class WebhookReceiver:
    """HTTP server that captures webhook requests for assertion.

    Typical usage::

        receiver = WebhookReceiver()
        receiver.start()
        try:
            # configure SUT to POST to receiver.url
            request = receiver.wait_for_request(timeout=10)
            assert request is not None
        finally:
            receiver.stop()
    """

    host: str = "0.0.0.0"
    _server: HTTPServer | None = field(default=None, init=False, repr=False)
    _thread: threading.Thread | None = field(default=None, init=False, repr=False)
    _requests: list[WebhookRequest] = field(default_factory=list, init=False, repr=False)
    _request_event: threading.Event = field(default_factory=threading.Event, init=False, repr=False)

    @property
    def port(self) -> int:
        """Return the port the server is listening on."""
        if self._server is None:
            raise RuntimeError("Server not started")
        return self._server.server_address[1]

    def url(self, webhook_host: str = "localhost") -> str:
        """Return the full webhook URL using the given host."""
        return f"http://{webhook_host}:{self.port}/webhook"

    def record_request(self, req: WebhookRequest) -> None:
        """Append a captured request and signal any waiters."""
        self._requests.append(req)
        self._request_event.set()

    def start(self) -> None:
        """Start the webhook receiver in a background thread."""
        receiver = self

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                """Handle POST requests from the SUT."""
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b""
                headers = dict(self.headers.items())
                req = WebhookRequest(
                    method="POST",
                    path=self.path,
                    headers=headers,
                    body=body,
                )
                receiver.record_request(req)
                self.send_response(200)
                self.end_headers()

            def log_message(self, format: str, *args: Any) -> None:
                """Suppress request logging."""

        self._server = HTTPServer((self.host, 0), _Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Shut down the server and join the background thread."""
        if self._server is not None:
            self._server.shutdown()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def clear(self) -> None:
        """Discard all captured requests."""
        self._requests.clear()
        self._request_event.clear()

    def wait_for_request(self, timeout: float = 10) -> WebhookRequest | None:
        """Block until a request arrives or *timeout* seconds elapse."""
        if self._requests:
            return self._requests[0]
        self._request_event.wait(timeout=timeout)
        return self._requests[0] if self._requests else None

    def get_requests(self) -> list[WebhookRequest]:
        """Return a copy of all captured requests."""
        return list(self._requests)
