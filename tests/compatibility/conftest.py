"""Shared pytest fixtures and hooks for A2A TCK tests."""

from __future__ import annotations

import re

from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import pytest

from tck.reporting.collector import CompatibilityCollector
from tck.transport.grpc_client import GrpcClient
from tck.transport.http_json_client import HttpJsonClient
from tck.transport.jsonrpc_client import JsonRpcClient
from tck.validators.json_schema import JSONSchemaValidator
from tck.validators.jsonrpc.response_validator import JsonRpcResponseValidator
from tck.validators.proto_schema import ProtoSchemaValidator
from tck.webhook.server import WebhookReceiver


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# Maps the agent card's protocolBinding value to (internal transport name, client class).
_PROTOCOL_BINDING_MAP: dict[str, tuple[str, type[BaseTransportClient]]] = {
    "JSONRPC": ("jsonrpc", JsonRpcClient),
    "GRPC": ("grpc", GrpcClient),
    "HTTP+JSON": ("http_json", HttpJsonClient),
}

# Transport markers used on tests as an alternative to parametrize.
_TRANSPORT_MARKERS = {"grpc", "jsonrpc", "http_json"}

# Pattern for extracting requirement IDs from docstrings.
_REQUIREMENT_ID_RE = re.compile(r"([A-Z][A-Z0-9_]+-[A-Z]+-\d+)")

# Stash keys for sharing data between fixtures and hooks.
_collector_key = pytest.StashKey[CompatibilityCollector]()
_agent_card_key = pytest.StashKey[dict]()
_record_count_key = pytest.StashKey[int]()


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
        "--compatibility-report",
        dest="compatibility_report",
        default=None,
        help="Output path for the compatibility report.",
    )
    group.addoption(
        "--webhook-host",
        dest="webhook_host",
        default="localhost",
        help=(
            "Hostname the SUT uses to reach the TCK webhook receiver "
            "(default: localhost)."
        ),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def sut_host(request: pytest.FixtureRequest) -> str:
    """Return the SUT hostname."""
    return request.config.getoption("--sut-host")


@pytest.fixture(scope="session")
def agent_card(request: pytest.FixtureRequest, sut_host: str) -> dict[str, Any]:
    """Fetch the agent card from the well-known URL.

    Per the A2A spec (Section 8.2), the agent card is discovered at
    ``{host}/.well-known/agent-card.json``.
    """
    base = sut_host.rstrip("/")
    url = f"{base}/.well-known/agent-card.json"
    response = httpx.get(url)
    response.raise_for_status()
    card = response.json()
    request.config.stash[_agent_card_key] = card
    return card


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
def webhook_host(request: pytest.FixtureRequest) -> str:
    """Return the hostname the SUT should use to reach the webhook receiver."""
    return request.config.getoption("--webhook-host")


@pytest.fixture(scope="session")
def webhook_receiver() -> WebhookReceiver:
    """Start a webhook receiver for the duration of the test session."""
    receiver = WebhookReceiver()
    receiver.start()
    yield receiver
    receiver.stop()


@pytest.fixture(scope="session")
def compatibility_collector(request: pytest.FixtureRequest) -> CompatibilityCollector:
    """Return a compatibility result collector.

    The collector is stashed on the config so that ``pytest_sessionfinish``
    can access it without touching private attributes.
    """
    collector = CompatibilityCollector()
    request.config.stash[_collector_key] = collector
    return collector


# ---------------------------------------------------------------------------
# Safety-net hook — auto-record failures for crashed tests
# ---------------------------------------------------------------------------


def _extract_requirement_and_transport(
    item: pytest.Item,
) -> tuple[str | None, str | None]:
    r"""Extract ``(requirement_id, transport)`` from a test item.

    * **Transport**: ``item.callspec.params["transport"]`` (parametrized) or
      a transport marker (``@grpc``, ``@jsonrpc``, ``@http_json``).
    * **Requirement ID**: first match of ``[A-Z][A-Z0-9_]+-[A-Z]+-\d+`` in
      the test function's docstring.

    Returns ``(None, None)`` when extraction fails so the caller can skip.
    """
    # --- transport ---
    transport: str | None = None
    callspec = getattr(item, "callspec", None)
    if callspec is not None:
        transport = callspec.params.get("transport")
    if transport is None:
        for marker_name in _TRANSPORT_MARKERS:
            if item.get_closest_marker(marker_name) is not None:
                transport = marker_name
                break

    # --- requirement ID ---
    requirement_id: str | None = None
    func = getattr(item, "function", None)
    if func is not None:
        docstring = func.__doc__ or ""
        m = _REQUIREMENT_ID_RE.search(docstring)
        if m:
            requirement_id = m.group(1)

    if transport is None or requirement_id is None:
        return None, None
    return requirement_id, transport


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Any:
    """Auto-record a compatibility failure when a test crashes without calling ``record()``."""
    outcome = yield
    report: pytest.TestReport = outcome.get_result()

    collector: CompatibilityCollector | None = item.config.stash.get(
        _collector_key, None
    )
    if collector is None:
        return

    if report.when == "setup":
        item.stash[_record_count_key] = collector.record_count
        collector.current_nodeid = item.nodeid
        return

    if report.when != "call":
        return
    if report.passed:
        return

    before = item.stash.get(_record_count_key, None)
    if before is None:
        return
    if collector.record_count != before:
        # Test already called record() — nothing to do.
        return

    requirement_id, transport = _extract_requirement_and_transport(item)
    if requirement_id is None or transport is None:
        return

    from tck.requirements.registry import get_requirement_by_id

    try:
        level = get_requirement_by_id(requirement_id).level.value
    except KeyError:
        level = "MUST"

    collector.record(
        requirement_id=requirement_id,
        transport=transport,
        passed=False,
        errors=[report.longreprtext],
        level=level,
        test_id=report.nodeid,
    )


# ---------------------------------------------------------------------------
# Session hooks — report generation
# ---------------------------------------------------------------------------


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Write compatibility reports and print console summary at session end."""
    collector = session.config.stash.get(_collector_key, None)
    if collector is None or not collector.get_results():
        return

    from tck.reporting.aggregator import CompatibilityAggregator
    from tck.reporting.console_formatter import ConsoleFormatter
    from tck.reporting.html_formatter import HTMLFormatter
    from tck.reporting.json_formatter import JSONFormatter

    sut_url: str = session.config.getoption("--sut-host", default="")
    agent_card = session.config.stash.get(_agent_card_key, None)
    report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()

    # Always print console summary
    console = ConsoleFormatter(sut_url=sut_url)
    session.config.pluginmanager.get_plugin("terminalreporter").write_line("")
    session.config.pluginmanager.get_plugin("terminalreporter").write_line(
        console.format(report)
    )

    # Write file report if --compatibility-report was given
    report_path_str: str | None = session.config.getoption(
        "--compatibility-report", default=None
    )
    if not report_path_str:
        return

    report_path = Path(report_path_str)
    HTMLFormatter(sut_url=sut_url).write(report, report_path.with_suffix(".html"))
    JSONFormatter(sut_url=sut_url).write(report, report_path.with_suffix(".json"))
