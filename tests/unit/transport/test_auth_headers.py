"""Tests for configured authentication headers in transport clients."""

from __future__ import annotations

import httpx
import pytest

from tck.transport import grpc_client
from tck.transport._helpers import build_default_headers, get_auth_headers, merge_headers
from tck.transport.grpc_client import GrpcClient
from tck.transport.http_json_client import HttpJsonClient
from tck.transport.jsonrpc_client import JsonRpcClient


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        (
            {"A2A_AUTH_TYPE": "bearer", "A2A_AUTH_TOKEN": "token"},
            {"authorization": "Bearer token"},
        ),
        (
            {"A2A_AUTH_TYPE": "basic", "A2A_AUTH_USERNAME": "user", "A2A_AUTH_PASSWORD": "pass"},
            {"authorization": "Basic dXNlcjpwYXNz"},
        ),
        (
            {"A2A_AUTH_TYPE": "apikey", "A2A_AUTH_TOKEN": "key"},
            {"x-api-key": "key"},
        ),
        (
            {
                "A2A_AUTH_TYPE": "custom",
                "A2A_AUTH_HEADER": "X-Service-Token",
                "A2A_AUTH_TOKEN": "token",
            },
            {"x-service-token": "token"},
        ),
        (
            {"A2A_AUTH_HEADERS": '{"Authorization":"Bearer token","X-Tenant-ID":"tenant"}'},
            {"authorization": "Bearer token", "x-tenant-id": "tenant"},
        ),
    ],
)
def test_get_auth_headers(env: dict[str, str], expected: dict[str, str]) -> None:
    """All documented authentication formats produce request headers."""
    assert get_auth_headers(env) == expected


def test_get_auth_headers_combines_explicit_headers_with_auth_type() -> None:
    """Explicit JSON headers override a derived authentication header."""
    headers = get_auth_headers(
        {
            "A2A_AUTH_TYPE": "bearer",
            "A2A_AUTH_TOKEN": "default",
            "A2A_AUTH_HEADERS": '{"authorization":"Bearer replacement","X-Tenant-ID":"tenant"}',
        }
    )

    assert headers == {"authorization": "Bearer replacement", "x-tenant-id": "tenant"}


def test_get_auth_headers_rejects_invalid_json() -> None:
    """Malformed JSON is reported before requests are sent."""
    with pytest.raises(ValueError, match="A2A_AUTH_HEADERS must contain a JSON object"):
        get_auth_headers({"A2A_AUTH_HEADERS": "not-json"})


def test_merge_headers_is_case_insensitive() -> None:
    """Per-call headers replace configured headers regardless of casing."""
    assert merge_headers({"Authorization": "Bearer default"}, {"authorization": "Bearer override"}) == {
        "authorization": "Bearer override"
    }


@pytest.mark.parametrize("client_type", [HttpJsonClient, JsonRpcClient])
def test_http_clients_inject_and_override_auth_headers(
    monkeypatch: pytest.MonkeyPatch,
    client_type: type[HttpJsonClient | JsonRpcClient],
) -> None:
    """HTTP clients send configured auth and allow per-call overrides."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={})

    original_client = httpx.Client

    def create_client(*args: object, **kwargs: object) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", create_client)
    monkeypatch.setenv("A2A_AUTH_TYPE", "bearer")
    monkeypatch.setenv("A2A_AUTH_TOKEN", "default")

    client = client_type("https://sut.example")
    try:
        client.get_extended_agent_card(extra_headers={"Authorization": "Bearer override"})
    finally:
        client.close()

    assert len(requests) == 1
    assert requests[0].headers["authorization"] == "Bearer override"
    assert requests[0].headers["a2a-version"] == "1.0"


def test_grpc_client_injects_and_overrides_auth_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    """GRPC metadata contains the configured and per-call authentication header."""
    captured_metadata: tuple[tuple[str, str], ...] | None = None

    class FakeChannel:
        def close(self) -> None:
            pass

    class FakeStub:
        def GetExtendedAgentCard(  # noqa: N802
            self,
            _request: object,
            *,
            timeout: float | None,
            metadata: tuple[tuple[str, str], ...],
        ) -> object:
            nonlocal captured_metadata
            captured_metadata = metadata
            return object()

    monkeypatch.setattr(grpc_client.grpc, "insecure_channel", lambda _target: FakeChannel())
    monkeypatch.setattr(grpc_client.a2a_pb2_grpc, "A2AServiceStub", lambda _channel: FakeStub())
    monkeypatch.setenv("A2A_AUTH_TYPE", "bearer")
    monkeypatch.setenv("A2A_AUTH_TOKEN", "default")

    client = GrpcClient("sut.example:443")
    try:
        client.get_extended_agent_card(extra_headers={"authorization": "Bearer override"})
    finally:
        client.close()

    assert dict(captured_metadata or ()) == {
        "a2a-version": "1.0",
        "authorization": "Bearer override",
    }


def test_default_headers_include_protocol_version_and_auth() -> None:
    """The common header builder keeps the protocol header with authentication."""
    assert build_default_headers({"A2A_AUTH_TYPE": "bearer", "A2A_AUTH_TOKEN": "token"}) == {
        "a2a-version": "1.0",
        "authorization": "Bearer token",
    }
