"""Shared test helper functions for compatibility tests.

Provides ``fail_msg``, ``record``, ``get_client``, and
``collect_events_with_timeout`` — utilities used across all conformance
test modules.
"""

from __future__ import annotations

import threading

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import TERMINAL_STATES


if TYPE_CHECKING:
    from tck.requirements.base import ErrorBinding, RequirementSpec
    from tck.transport.base import BaseTransportClient


def expected_error_of(req: RequirementSpec) -> ErrorBinding:
    """Return a requirement's declared ``expected_error``, asserting it is set.

    The registry invariant (``test_expected_error_declared``) guarantees that
    any requirement whose text mandates a specific error declares it here, so a
    missing binding is a registry bug, not a runtime condition.
    """
    if req.expected_error is None:
        raise AssertionError(f"{req.id} does not declare an expected_error")
    return req.expected_error


_GRPC_TERMINAL_STATES = frozenset(s.grpc_value for s in TERMINAL_STATES)

_JSON_TERMINAL_STATES = frozenset(s.json_value for s in TERMINAL_STATES)


def is_terminal_status(response: Any, transport: str) -> bool:
    """Return True if *response* carries a task in a terminal state.

    Handles both the ``SendMessageResponse`` payload oneof (gRPC) or
    ``result`` envelope (JSON-RPC) and a bare ``Task`` returned by
    GetTask/CancelTask.
    """
    raw = response.raw_response
    if transport == "grpc":
        # SendMessageResponse has a "payload" oneof; Task proto does not.
        try:
            payload = raw.WhichOneof("payload")
            if payload == "task":
                return raw.task.status.state in _GRPC_TERMINAL_STATES
        except (ValueError, AttributeError):
            pass
        # Task proto returned directly (GetTask, CancelTask)
        if hasattr(raw, "status"):
            return raw.status.state in _GRPC_TERMINAL_STATES
        return False

    # JSON-RPC or HTTP+JSON
    if not isinstance(raw, dict):
        return False
    if transport == "jsonrpc":
        result = raw.get("result", {})
        task = result.get("task", result) if isinstance(result, dict) else {}
    else:
        task = raw.get("task", raw)

    if isinstance(task, dict):
        status = task.get("status", {})
        state = status.get("state", "") if isinstance(status, dict) else ""
        return state in _JSON_TERMINAL_STATES
    return False


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


_DEFAULT_STREAM_TIMEOUT_S = 10


def collect_events_with_timeout(
    events_iter: Any,
    timeout: float = _DEFAULT_STREAM_TIMEOUT_S,
    *,
    stop_after_first: bool = False,
) -> tuple[list[Any], bool]:
    """Collect streaming events with a hard wall-clock timeout.

    Runs event consumption in a daemon thread so that we can enforce
    the deadline even when ``next(events_iter)`` itself blocks
    (e.g. an SSE connection waiting for data that never arrives).

    When *stop_after_first* is ``True`` the iterator is abandoned after the
    first event — used to simulate a client closing a stream early.

    Returns a tuple of (events, timed_out).
    """
    collected: list[Any] = []

    def _drain() -> None:
        try:
            for event in events_iter:
                collected.append(event)
                if stop_after_first:
                    break
        except Exception:
            pass

    thread = threading.Thread(target=_drain, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    timed_out = thread.is_alive()
    return collected, timed_out
