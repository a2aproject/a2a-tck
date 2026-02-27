"""Shared pytest fixtures for A2A TCK tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import pytest

from tck.reporting.collector import ComplianceCollector
from tck.transport.grpc_client import GrpcClient
from tck.transport.http_json_client import HttpJsonClient
from tck.transport.jsonrpc_client import JsonRpcClient
from tck.validators.json_schema import JSONSchemaValidator
from tck.validators.jsonrpc.response_validator import JsonRpcResponseValidator
from tck.validators.proto_schema import ProtoSchemaValidator


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# Maps the agent card's protocolBinding value to (internal transport name, client class).
_PROTOCOL_BINDING_MAP: dict[str, tuple[str, type[BaseTransportClient]]] = {
    "JSONRPC": ("jsonrpc", JsonRpcClient),
    "GRPC": ("grpc", GrpcClient),
    "HTTP+JSON": ("http_json", HttpJsonClient),
}


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register A2A TCK CLI options."""
    group = parser.getgroup("a2a-tck", "A2A TCK options")
    group.addoption(
        "--sut-host",
        dest="sut_host",
        default="http://localhost",
        help="Hostname of the System Under Test (default: http://localhost).",
    )
    group.addoption(
        "--transport",
        dest="transport",
        default="all",
        help=(
            'Transport filter: "all" (default) or comma-separated list '
            '(e.g. "grpc,jsonrpc,http_json").'
        ),
    )
    group.addoption(
        "--compliance-report",
        dest="compliance_report",
        default=None,
        help="Output path for the compliance report.",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def sut_host(request: pytest.FixtureRequest) -> str:
    """Return the SUT hostname."""
    return request.config.getoption("--sut-host")


@pytest.fixture(scope="session")
def agent_card(sut_host: str) -> dict[str, Any]:
    """Fetch the agent card from the well-known URL.

    Per the A2A spec (Section 8.2), the agent card is discovered at
    ``{host}/.well-known/agent-card.json``.
    """
    base = sut_host.rstrip("/")
    url = f"{base}/.well-known/agent-card.json"
    response = httpx.get(url)
    response.raise_for_status()
    return response.json()


@pytest.fixture(scope="session")
def transport_clients(
    request: pytest.FixtureRequest,
    agent_card: dict[str, Any],
) -> dict[str, BaseTransportClient]:
    """Create transport clients from the agent card's ``supportedInterfaces``.

    Each interface declares a ``protocolBinding`` (JSONRPC / GRPC / HTTP+JSON)
    and a ``url`` where that transport is available.  Clients are created using
    the per-interface URL.  When multiple interfaces share the same binding,
    the first one wins (per the spec's preference-order rule).

    The ``--transport`` CLI option further restricts which transports are used.
    """
    interfaces = agent_card.get("supportedInterfaces", [])
    if not interfaces:
        pytest.fail(
            "Agent card declares no supportedInterfaces — "
            "cannot determine which transports to test"
        )

    # Parse --transport filter
    raw: str = request.config.getoption("--transport")
    if raw == "all":
        transport_filter: set[str] | None = None
    else:
        transport_filter = {t.strip() for t in raw.split(",") if t.strip()}

    clients: dict[str, BaseTransportClient] = {}
    for iface in interfaces:
        binding = iface.get("protocolBinding", "")
        url = iface.get("url", "")

        entry = _PROTOCOL_BINDING_MAP.get(binding)
        if entry is None:
            continue  # Unknown binding, skip

        transport_name, client_class = entry

        # Respect --transport filter
        if transport_filter is not None and transport_name not in transport_filter:
            continue

        # First interface per transport wins (preference order)
        if transport_name not in clients:
            clients[transport_name] = client_class(url)

    if not clients:
        declared = [iface.get("protocolBinding", "?") for iface in interfaces]
        pytest.fail(
            f"No usable transports after filtering.  "
            f"Agent card declares: {declared}.  "
            f"--transport filter: {raw!r}"
        )

    yield clients

    for client in clients.values():
        client.close()


@pytest.fixture(scope="session")
def validators() -> dict[str, Any]:
    """Return a dict of validators keyed by transport name."""
    schema_path = Path(__file__).parent.parent.parent / "specification" / "a2a.json"
    json_schema_validator = JSONSchemaValidator(schema_path)
    return {
        "grpc": ProtoSchemaValidator(),
        "jsonrpc": JsonRpcResponseValidator(json_schema_validator),
        "http_json": json_schema_validator,
    }


@pytest.fixture(scope="session")
def compliance_collector() -> ComplianceCollector:
    """Return a compliance result collector."""
    return ComplianceCollector()
