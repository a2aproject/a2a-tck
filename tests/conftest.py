"""Shared pytest fixtures for A2A TCK tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import pytest

from tck.transport import ALL_TRANSPORTS, TransportManager
from tck.validators.json_schema import JSONSchemaValidator
from tck.validators.proto_schema import ProtoSchemaValidator


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register A2A TCK CLI options."""
    group = parser.getgroup("a2a-tck", "A2A TCK options")
    group.addoption(
        "--sut-host",
        dest="sut_host",
        default="localhost",
        help="Hostname of the System Under Test (default: localhost).",
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
# Placeholder for ComplianceCollector (will be replaced by task 5.3)
# ---------------------------------------------------------------------------
@dataclass
class _ComplianceCollector:
    """Minimal placeholder until the real ComplianceCollector is built."""

    _results: list[dict[str, Any]] = field(default_factory=list)

    def record(self, **kwargs: Any) -> None:
        self._results.append(kwargs)

    def get_results(self) -> list[dict[str, Any]]:
        return list(self._results)

    def reset(self) -> None:
        self._results.clear()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def sut_host(request: pytest.FixtureRequest) -> str:
    """Return the SUT hostname."""
    return request.config.getoption("--sut-host")


@pytest.fixture(scope="session")
def transport_clients(
    request: pytest.FixtureRequest, sut_host: str
) -> dict[str, Any]:
    """Create and yield transport clients, closing them on teardown."""
    raw: str = request.config.getoption("--transport")
    if raw == "all":
        transports = None  # TransportManager defaults to ALL_TRANSPORTS
    else:
        transports = [t.strip() for t in raw.split(",") if t.strip()]

    manager = TransportManager(sut_host, transports)
    yield manager.get_all_clients()
    manager.close()


@pytest.fixture(scope="session")
def validators() -> dict[str, Any]:
    """Return a dict of validators keyed by transport name."""
    schema_path = Path(__file__).parent.parent / "specification" / "a2a.json"
    return {
        "grpc": ProtoSchemaValidator(),
        "jsonrpc": JSONSchemaValidator(schema_path),
        "http_json": JSONSchemaValidator(schema_path),
    }


@pytest.fixture(scope="session")
def compliance_collector() -> _ComplianceCollector:
    """Return a compliance result collector (placeholder)."""
    return _ComplianceCollector()


@pytest.fixture(scope="session")
def agent_card(sut_host: str) -> dict[str, Any]:
    """Fetch the agent card from the well-known URL.

    Per the A2A spec, the agent card is discovered at
    ``https://{host}/.well-known/agent-card.json``.
    """
    url = f"https://{sut_host}/.well-known/agent-card.json"
    response = httpx.get(url)
    response.raise_for_status()
    return response.json()
