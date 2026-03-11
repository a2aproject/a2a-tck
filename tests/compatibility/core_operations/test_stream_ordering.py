"""Cross-transport streaming event ordering test.

Validates that streaming events are delivered in generation order:
task states must not regress, and the last event must carry a terminal state.

Requirements tested:
    STREAM-ORDER-001 — Events delivered in generation order
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from specification.generated import a2a_pb2
from tck.requirements.registry import get_requirement_by_id
from tck.transport import ALL_TRANSPORTS
from tests.compatibility._test_helpers import fail_msg, get_client, record
from tests.compatibility.markers import streaming


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

STREAM_ORDER_001 = get_requirement_by_id("STREAM-ORDER-001")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SAMPLE_MESSAGE = {
    "role": "ROLE_USER",
    "parts": [{"text": "TCK stream ordering test"}],
    "messageId": "tck-stream-ordering-001",
}

# gRPC proto state ordering (numeric enum values)
_GRPC_STATE_ORDER = {
    a2a_pb2.TASK_STATE_SUBMITTED: 0,
    a2a_pb2.TASK_STATE_WORKING: 1,
    a2a_pb2.TASK_STATE_INPUT_REQUIRED: 1,
    a2a_pb2.TASK_STATE_AUTH_REQUIRED: 1,
    a2a_pb2.TASK_STATE_COMPLETED: 2,
    a2a_pb2.TASK_STATE_FAILED: 2,
    a2a_pb2.TASK_STATE_CANCELED: 2,
    a2a_pb2.TASK_STATE_REJECTED: 2,
}

_GRPC_TERMINAL_STATES = frozenset({
    a2a_pb2.TASK_STATE_COMPLETED,
    a2a_pb2.TASK_STATE_FAILED,
    a2a_pb2.TASK_STATE_CANCELED,
    a2a_pb2.TASK_STATE_REJECTED,
})

# JSON state ordering (lowercase string comparison)
_JSON_STATE_ORDER = {
    "submitted": 0,
    "working": 1,
    "input_required": 1,
    "auth_required": 1,
    "completed": 2,
    "failed": 2,
    "canceled": 2,
    "rejected": 2,
}

_JSON_TERMINAL_STATES = frozenset({"completed", "failed", "canceled", "rejected"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_streaming_events(
    client: BaseTransportClient,
    agent_card: dict[str, Any],
) -> list[Any]:
    """Send a streaming message and return collected events.

    Skips the test if the agent does not support streaming or
    if the streaming call fails.
    """
    caps = agent_card.get("capabilities", {})
    if not caps.get("streaming"):
        pytest.skip("Agent does not support streaming")

    response = client.send_streaming_message(message=_SAMPLE_MESSAGE)
    if getattr(response, "timed_out", False):
        pytest.skip("Streaming call timed out")
    if not response.success:
        pytest.skip(f"Streaming call failed: {response.error}")

    events = list(response.events)
    if not events:
        pytest.skip("Server returned no streaming events")

    return events


def _get_event_state_grpc(event: Any) -> int | None:
    """Extract task state from a gRPC StreamResponse event."""
    payload = event.WhichOneof("payload")
    if payload == "task":
        return event.task.status.state
    if payload == "status_update":
        return event.status_update.status.state
    return None


def _normalize_json_state(state: str) -> str:
    """Normalize a JSON state string for ordering comparison.

    Handles both ``TASK_STATE_COMPLETED`` and ``completed`` formats.
    """
    lower = state.lower()
    if lower.startswith("task_state_"):
        return lower[len("task_state_"):]
    return lower


def _get_event_state_json(event: dict) -> str | None:
    """Extract task state string from a JSON streaming event."""
    result = event.get("result", event)
    if not isinstance(result, dict):
        return None
    # Check statusUpdate first, then task
    status_update = result.get("statusUpdate", result.get("status_update"))
    if isinstance(status_update, dict):
        status = status_update.get("status", {})
        if isinstance(status, dict) and "state" in status:
            return _normalize_json_state(status["state"])
    task = result.get("task")
    if isinstance(task, dict):
        status = task.get("status", {})
        if isinstance(status, dict) and "state" in status:
            return _normalize_json_state(status["state"])
    return None


def _check_ordering_grpc(events: list[Any]) -> list[str]:
    """Check gRPC event ordering: no state regression, last event terminal."""
    errors: list[str] = []
    max_order = -1
    for i, event in enumerate(events):
        state = _get_event_state_grpc(event)
        if state is None:
            continue
        order = _GRPC_STATE_ORDER.get(state, -1)
        if order < max_order:
            errors.append(
                f"Event {i}: state {a2a_pb2.TaskState.Name(state)} "
                f"regresses from a later state"
            )
        else:
            max_order = order

    last_state = _get_event_state_grpc(events[-1])
    if last_state is not None and last_state not in _GRPC_TERMINAL_STATES:
        errors.append(
            f"Last event state {a2a_pb2.TaskState.Name(last_state)} "
            f"is not terminal"
        )
    return errors


def _check_ordering_json(events: list[dict]) -> list[str]:
    """Check JSON event ordering: no state regression, last event terminal."""
    errors: list[str] = []
    max_order = -1
    for i, event in enumerate(events):
        state = _get_event_state_json(event)
        if state is None:
            continue
        order = _JSON_STATE_ORDER.get(state, -1)
        if order < max_order:
            errors.append(
                f"Event {i}: state {state!r} regresses from a later state"
            )
        else:
            max_order = order

    last_state = _get_event_state_json(events[-1])
    if last_state is not None and last_state not in _JSON_TERMINAL_STATES:
        errors.append(
            f"Last event state {last_state!r} is not terminal"
        )
    return errors


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@streaming
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestStreamEventOrdering:
    """Validate streaming event ordering across all transports."""

    def test_streaming_event_ordering(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """STREAM-ORDER-001: Task states do not regress; last event is terminal."""
        req = STREAM_ORDER_001
        client = get_client(
            transport_clients, transport,
            compliance_collector=compliance_collector, req=req,
        )
        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(
                collector=compliance_collector, req=req,
                transport=transport, passed=False, skipped=True,
            )
            pytest.skip("Agent does not support streaming")

        events = _get_streaming_events(client, agent_card)

        errors = _check_ordering_grpc(events) if transport == "grpc" else _check_ordering_json(events)

        passed = not errors
        record(
            collector=compliance_collector, req=req,
            transport=transport, passed=passed, errors=errors,
        )
        assert passed, fail_msg(req, transport, "; ".join(errors))
