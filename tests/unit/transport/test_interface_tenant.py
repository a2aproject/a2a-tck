"""The transport clients apply the tenant an ``AgentInterface`` declares.

Specification section 8.3 tells a client to set the ``tenant`` field in every
request to exactly the value declared by the interface it selected, and to omit
it when the interface declares none.  The HTTP+JSON binding carries it as a path
prefix (``/{tenant}/message:send``), JSON-RPC as ``params.tenant`` and gRPC as the
``tenant`` field of the request message.
"""

from __future__ import annotations

import json
import threading

from concurrent import futures
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Iterator

import grpc
import pytest

from specification.generated import a2a_pb2, a2a_pb2_grpc
from tck.transport.grpc_client import GrpcClient
from tck.transport.http_json_client import HttpJsonClient
from tck.transport.jsonrpc_client import JsonRpcClient


_TENANT = "acme"
_MESSAGE = {"role": "ROLE_USER", "parts": [{"text": "hi"}], "messageId": "tenant-test"}


class _Recorder(BaseHTTPRequestHandler):
    """Answers any POST with an empty JSON object and records the path and body."""

    seen: list[tuple[str, Any]] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else None
        type(self).seen.append((self.path, body))
        payload = b"{}"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:
        pass


@pytest.fixture
def http_server() -> Iterator[tuple[str, list[tuple[str, Any]]]]:
    """A stdlib HTTP server and the list of ``(path, body)`` pairs it has received."""
    handler = type("Handler", (_Recorder,), {"seen": []})
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", handler.seen
    finally:
        server.shutdown()
        server.server_close()


def test_http_json_prefixes_the_declared_tenant(http_server: tuple[str, list[tuple[str, Any]]]) -> None:
    """A declared tenant becomes the first path segment of a unary call."""
    url, seen = http_server
    client = HttpJsonClient(url, tenant=_TENANT)
    try:
        client.send_message(message=_MESSAGE)
        assert seen[-1][0] == f"/{_TENANT}/message:send"
    finally:
        client.close()


def test_http_json_streaming_prefixes_the_declared_tenant(http_server: tuple[str, list[tuple[str, Any]]]) -> None:
    """A declared tenant becomes the first path segment of a streaming call."""
    url, seen = http_server
    client = HttpJsonClient(url, tenant=_TENANT)
    try:
        client.send_streaming_message(message=_MESSAGE)
        assert seen[-1][0] == f"/{_TENANT}/message:stream"
    finally:
        client.close()


def test_http_json_adds_nothing_without_a_declared_tenant(http_server: tuple[str, list[tuple[str, Any]]]) -> None:
    """Without a declared tenant the path is left as the binding defines it."""
    url, seen = http_server
    client = HttpJsonClient(url)
    try:
        client.send_message(message=_MESSAGE)
        assert seen[-1][0] == "/message:send"
    finally:
        client.close()


def test_jsonrpc_sends_the_declared_tenant_in_params(http_server: tuple[str, list[tuple[str, Any]]]) -> None:
    """A declared tenant is sent in ``params`` of every call."""
    url, seen = http_server
    client = JsonRpcClient(url, tenant=_TENANT)
    try:
        client.send_message(message=_MESSAGE)
        assert seen[-1][1]["params"]["tenant"] == _TENANT
        client.get_task(id="t-1")
        assert seen[-1][1]["params"]["tenant"] == _TENANT
    finally:
        client.close()


def test_jsonrpc_omits_the_tenant_when_none_is_declared(http_server: tuple[str, list[tuple[str, Any]]]) -> None:
    """Without a declared tenant ``params`` has no ``tenant`` key."""
    url, seen = http_server
    client = JsonRpcClient(url)
    try:
        client.send_message(message=_MESSAGE)
        assert "tenant" not in seen[-1][1]["params"]
    finally:
        client.close()


class _TenantRecorder(a2a_pb2_grpc.A2AServiceServicer):
    """Records the ``tenant`` field of every SendMessage and GetTask it receives."""

    def __init__(self) -> None:
        self.tenants: list[str] = []

    def SendMessage(self, request: Any, context: Any) -> Any:  # noqa: N802 - gRPC method name
        self.tenants.append(request.tenant)
        return a2a_pb2.SendMessageResponse()

    def GetTask(self, request: Any, context: Any) -> Any:  # noqa: N802 - gRPC method name
        self.tenants.append(request.tenant)
        return a2a_pb2.Task()


@pytest.fixture
def grpc_server() -> Iterator[tuple[str, _TenantRecorder]]:
    """An in-process gRPC server and the servicer recording the tenants it receives."""
    servicer = _TenantRecorder()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    a2a_pb2_grpc.add_A2AServiceServicer_to_server(servicer, server)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    try:
        yield f"127.0.0.1:{port}", servicer
    finally:
        server.stop(grace=None)


def test_grpc_sets_the_declared_tenant_on_the_request(grpc_server: tuple[str, _TenantRecorder]) -> None:
    """A declared tenant is set on every request message."""
    address, servicer = grpc_server
    client = GrpcClient(address, tenant=_TENANT)
    try:
        client.send_message(message=_MESSAGE)
        client.get_task(id="t-1")
        assert servicer.tenants == [_TENANT, _TENANT]
    finally:
        client.close()


def test_grpc_leaves_the_tenant_unset_when_none_is_declared(grpc_server: tuple[str, _TenantRecorder]) -> None:
    """Without a declared tenant the request's ``tenant`` stays empty."""
    address, servicer = grpc_server
    client = GrpcClient(address)
    try:
        client.send_message(message=_MESSAGE)
        assert servicer.tenants == [""]
    finally:
        client.close()
