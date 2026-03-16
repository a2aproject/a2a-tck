"""Shared test helper functions for compatibility tests.

Provides ``fail_msg``, ``record``, and ``get_client`` — utilities used
across all conformance test modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest


if TYPE_CHECKING:
    from tck.requirements.base import RequirementSpec
    from tck.transport.base import BaseTransportClient


def fail_msg(req: RequirementSpec, transport: str, detail: str) -> str:
    """Build a failure message referencing the requirement."""
    return (
        f"{req.id} [{req.title}] failed on {transport}: "
        f"{detail} (see {req.spec_url})"
    )


def record(
    collector: Any,
    req: RequirementSpec,
    transport: str,
    passed: bool,
    errors: list[str] | None = None,
    *,
    skipped: bool = False,
) -> None:
    """Record a result in the compatibility collector."""
    collector.record(
        requirement_id=req.id,
        transport=transport,
        level=req.level.value,
        passed=passed,
        errors=errors or [],
        skipped=skipped,
    )


def assert_and_record(
    collector: Any,
    req: RequirementSpec,
    transport: str,
    errors: list[str],
) -> None:
    """Record the result and assert no errors."""
    passed = not errors
    record(collector, req, transport, passed=passed, errors=errors)
    assert passed, fail_msg(req, transport, "; ".join(errors))


def get_client(
    transport_clients: dict[str, BaseTransportClient],
    transport: str,
    *,
    compatibility_collector: Any = None,
    req: Any = None,
) -> BaseTransportClient:
    """Get the transport client, skipping if not configured."""
    client = transport_clients.get(transport)
    if client is None:
        if compatibility_collector is not None and req is not None:
            record(compatibility_collector, req, transport, passed=False, skipped=True)
        pytest.skip(f"Transport {transport!r} not configured")
    return client
