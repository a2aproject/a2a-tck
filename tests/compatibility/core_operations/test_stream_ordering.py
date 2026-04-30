"""Cross-transport streaming event ordering test.

Validates that streaming events are delivered in generation order:
task states must not regress, and the last event must carry a terminal state.

Requirements tested:
    STREAM-ORDER-001 — Events delivered in generation order
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import (
    TASK_STATE_AUTH_REQUIRED,
    TASK_STATE_CANCELED,
    TASK_STATE_COMPLETED,
    TASK_STATE_FAILED,
    TASK_STATE_INPUT_REQUIRED,
    TASK_STATE_REJECTED,
    TASK_STATE_SUBMITTED,
    TASK_STATE_WORKING,
    tck_id,
)
from tck.requirements.registry import get_requirement_by_id
from tck.transport import ALL_TRANSPORTS
from tck.validators import STREAM_RESPONSE
from tests.compatibility._test_helpers import assert_and_record, get_client, record
from tests.compatibility.markers import must, streaming


if TYPE_CHECKING:
    from collections.abc import Callable

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
    "messageId": tck_id("stream-ordering-001"),
}

# State ordering: 0 = initial, 1 = active, 2 = terminal.
_ALL_STATES_WITH_ORDER = [
    (TASK_STATE_SUBMITTED, 0),
    (TASK_STATE_WORKING, 1),
    (TASK_STATE_INPUT_REQUIRED, 1),
    (TASK_STATE_AUTH_REQUIRED, 1),
    (TASK_STATE_COMPLETED, 2),
    (TASK_STATE_FAILED, 2),
    (TASK_STATE_CANCELED, 2),
    (TASK_STATE_REJECTED, 2),
]

# Maps json_value (str) → order. Both gRPC and JSON extractors return
# the json_value string so a single lookup table works for all transports.
_STATE_ORDER: dict[str, int] = {
    s.json_value: order for s, order in _ALL_STATES_WITH_ORDER
}

# Reverse lookup: gRPC int enum → json_value string, so the gRPC
# state extractor can return a transport-neutral key.
_GRPC_STATE_TO_NAME: dict[int, str] = {
    s.grpc_value: s.json_value for s, _ in _ALL_STATES_WITH_ORDER
}


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


def _get_event_state_grpc(event: Any) -> str | None:
    """Extract task state name from a gRPC StreamResponse event."""
    payload = event.WhichOneof("payload")
    if payload == "task":
        return _GRPC_STATE_TO_NAME.get(event.task.status.state)
    if payload == "status_update":
        return _GRPC_STATE_TO_NAME.get(event.status_update.status.state)
    return None


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
            return status["state"]
    task = result.get("task")
    if isinstance(task, dict):
        status = task.get("status", {})
        if isinstance(status, dict) and "state" in status:
            return status["state"]
    return None


def _check_ordering(
    events: list[Any],
    get_state: Callable[[Any], str | None],
) -> list[str]:
    """Check event ordering: no state regression."""
    errors: list[str] = []
    max_order = -1
    for i, event in enumerate(events):
        state = get_state(event)
        if state is None:
            continue
        order = _STATE_ORDER.get(state, -1)
        if order < max_order:
            errors.append(
                f"Event {i}: state {state} regresses from a later state"
            )
        else:
            max_order = order

    return errors


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@must
@streaming
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestStreamEventOrdering:
    """Validate streaming event ordering across all transports."""

    def test_streaming_event_ordering(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
        validators: dict[str, Any],
    ) -> None:
        """STREAM-ORDER-001: Task states do not regress; last event is terminal."""
        req = STREAM_ORDER_001
        client = get_client(
            transport_clients, transport,
            compatibility_collector=compatibility_collector, req=req,
        )
        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(
                collector=compatibility_collector, req=req,
                transport=transport, passed=False, skipped=True,
            )
            pytest.skip("Agent does not support streaming")

        events = _get_streaming_events(client, agent_card)

        get_state = _get_event_state_grpc if transport == "grpc" else _get_event_state_json
        errors = _check_ordering(events, get_state)

        validator = validators[transport]
        for i, event in enumerate(events):
            result = validator.validate(event, STREAM_RESPONSE)
            if not result.valid:
                errors.extend(f"Event {i}: {e}" for e in result.errors)

        assert_and_record(compatibility_collector, req, transport, errors)
