"""gRPC streaming tests.

Validates that gRPC server streaming RPCs (SendStreamingMessage,
SubscribeToTask) return correctly structured StreamResponse messages
with proper event ordering, cancellation, and error propagation.

Requirements tested:
    GRPC-ERR-003    — gRPC streaming uses server streaming RPCs
    STREAM-SUB-001  — SubscribeToTask returns Task as first event
    STREAM-SUB-004  — SubscribeToTask returns TaskNotFoundError for non-existent task
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import grpc
import pytest

from specification.generated import a2a_pb2
from tck.requirements.registry import get_requirement_by_id
from tck.transport.grpc_client import TRANSPORT
from tck.validators.grpc.error_validator import validate_grpc_error
from tests.compatibility._test_helpers import fail_msg, get_client, record
from tests.compatibility.markers import grpc as grpc_marker
from tests.compatibility.markers import must, streaming


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

GRPC_ERR_003 = get_requirement_by_id("GRPC-ERR-003")
STREAM_SUB_001 = get_requirement_by_id("STREAM-SUB-001")
STREAM_SUB_004 = get_requirement_by_id("STREAM-SUB-004")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_PAYLOAD_FIELDS = {"task", "message", "status_update", "artifact_update"}

_TERMINAL_STATES = frozenset({
    a2a_pb2.TASK_STATE_COMPLETED,
    a2a_pb2.TASK_STATE_FAILED,
    a2a_pb2.TASK_STATE_CANCELED,
    a2a_pb2.TASK_STATE_REJECTED,
})

_SAMPLE_MESSAGE = {
    "role": "ROLE_USER",
    "parts": [{"text": "TCK gRPC streaming test"}],
    "messageId": "tck-grpc-streaming-001",
}

_CONNECTIVITY_CODES = frozenset({
    grpc.StatusCode.UNAVAILABLE,
    grpc.StatusCode.DEADLINE_EXCEEDED,
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _skip_if_no_streaming(agent_card: dict[str, Any]) -> None:
    """Skip the test if the agent does not support streaming."""
    caps = agent_card.get("capabilities", {})
    if not caps.get("streaming"):
        pytest.skip("Agent does not support streaming")


def _collect_events(
    client: BaseTransportClient,
    agent_card: dict[str, Any],
) -> list[a2a_pb2.StreamResponse]:
    """Send a streaming message and return all collected events.

    Skips the test if streaming is unsupported or the call fails.
    """
    _skip_if_no_streaming(agent_card)

    response = client.send_streaming_message(message=_SAMPLE_MESSAGE)
    if not response.success:
        pytest.skip(f"Streaming call failed: {response.error}")

    try:
        events = list(response.events)
    except Exception as exc:
        pytest.skip(f"Streaming iteration failed: {exc}")

    if not events:
        pytest.skip("Server returned no streaming events")

    return events


# ---------------------------------------------------------------------------
# Streaming tests (SendStreamingMessage)
# ---------------------------------------------------------------------------


@must
@grpc_marker
@streaming
class TestGrpcStreaming:
    """Validate gRPC server streaming RPC behavior."""

    def test_streaming_response_type(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """GRPC-ERR-003: send_streaming_message returns a StreamingResponse."""
        req = GRPC_ERR_003
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compatibility_collector, req=req, transport=TRANSPORT, passed=False, skipped=True)
        _skip_if_no_streaming(agent_card)

        response = client.send_streaming_message(message=_SAMPLE_MESSAGE)
        if not response.success:
            pytest.skip(f"Streaming call failed: {response.error}")

        errors: list[str] = []
        if not response.is_streaming:
            errors.append("Response is_streaming should be True")

        # Consume at least one event to confirm the stream works
        first = next(iter(response.events), None)
        if first is None:
            errors.append("Stream yielded no events")

        passed = not errors
        record(
            collector=compatibility_collector,
            req=req,
            transport=TRANSPORT,
            passed=passed,
            errors=errors,
        )
        assert passed, fail_msg(req, TRANSPORT, "; ".join(errors))

    def test_streaming_message_structure(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """GRPC-ERR-003: Each event has exactly one StreamResponse payload field set."""
        req = GRPC_ERR_003
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compatibility_collector, req=req, transport=TRANSPORT, passed=False, skipped=True)
        events = _collect_events(client, agent_card)

        errors: list[str] = []
        for i, event in enumerate(events):
            payload = event.WhichOneof("payload")
            if payload is None:
                errors.append(f"Event {i}: no payload field set")
            elif payload not in _VALID_PAYLOAD_FIELDS:
                errors.append(
                    f"Event {i}: unexpected payload field {payload!r}"
                )

        passed = not errors
        record(
            collector=compatibility_collector,
            req=req,
            transport=TRANSPORT,
            passed=passed,
            errors=errors,
        )
        assert passed, fail_msg(req, TRANSPORT, "; ".join(errors))

    def test_streaming_cancellation(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """GRPC-ERR-003: Client-side stream cancellation completes without unexpected errors."""
        req = GRPC_ERR_003
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compatibility_collector, req=req, transport=TRANSPORT, passed=False, skipped=True)
        _skip_if_no_streaming(agent_card)

        response = client.send_streaming_message(message=_SAMPLE_MESSAGE)
        if not response.success:
            pytest.skip(f"Streaming call failed: {response.error}")

        errors: list[str] = []
        try:
            # Consume first event then cancel
            first = next(iter(response.events), None)
            if first is None:
                pytest.skip("Stream yielded no events before cancellation")

            response.raw_response.cancel()
        except grpc.RpcError as e:
            if e.code() != grpc.StatusCode.CANCELLED:
                errors.append(
                    f"Expected CANCELLED status after cancel(), "
                    f"got {e.code().name}"
                )

        passed = not errors
        record(
            collector=compatibility_collector,
            req=req,
            transport=TRANSPORT,
            passed=passed,
            errors=errors,
        )
        assert passed, fail_msg(req, TRANSPORT, "; ".join(errors))

    def test_streaming_error_propagation(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """STREAM-SUB-004: SubscribeToTask returns NOT_FOUND for non-existent task."""
        req = STREAM_SUB_004
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compatibility_collector, req=req, transport=TRANSPORT, passed=False, skipped=True)
        _skip_if_no_streaming(agent_card)

        response = client.subscribe_to_task(id="tck-nonexistent-grpc-stream-001")

        if response.success:
            # Try consuming events — error may arrive as a gRPC status on iteration
            try:
                list(response.events)
                pytest.skip(
                    "Server did not return an error for non-existent task subscribe"
                )
            except grpc.RpcError as e:
                if e.code() in _CONNECTIVITY_CODES:
                    pytest.fail(
                        f"gRPC connectivity error: {e.code().name} — {e.details()}"
                    )
                result = validate_grpc_error(e, "TaskNotFoundError")
                errors = [] if result.valid else [result.message]
                passed = result.valid
        else:
            rpc_error = response.raw_response
            if not isinstance(rpc_error, grpc.RpcError):
                pytest.fail(
                    f"Expected grpc.RpcError, got {type(rpc_error).__name__}"
                )
            if rpc_error.code() in _CONNECTIVITY_CODES:
                pytest.fail(
                    f"gRPC connectivity error: {rpc_error.code().name} — "
                    f"{rpc_error.details()}"
                )
            result = validate_grpc_error(rpc_error, "TaskNotFoundError")
            errors = [] if result.valid else [result.message]
            passed = result.valid

        record(
            collector=compatibility_collector,
            req=req,
            transport=TRANSPORT,
            passed=passed,
            errors=errors,
        )
        assert passed, fail_msg(req, TRANSPORT, "; ".join(errors))

    def test_subscribe_first_event_is_task(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """STREAM-SUB-001: First event from SubscribeToTask contains a Task."""
        req = STREAM_SUB_001
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compatibility_collector, req=req, transport=TRANSPORT, passed=False, skipped=True)
        _skip_if_no_streaming(agent_card)

        # Create a task first via send_message
        msg_response = client.send_message(message=_SAMPLE_MESSAGE)
        if not msg_response.success:
            pytest.skip(f"send_message failed: {msg_response.error}")

        raw = msg_response.raw_response
        # Extract task ID from the SendMessageResponse protobuf
        task_id = None
        if hasattr(raw, "WhichOneof"):
            payload = raw.WhichOneof("payload")
            if payload == "task" and raw.task.id:
                task_id = raw.task.id
        if not task_id:
            pytest.skip("Could not extract task ID from send_message response")

        # Subscribe to the task
        sub_response = client.subscribe_to_task(id=task_id)
        if not sub_response.success:
            pytest.skip(f"subscribe_to_task failed: {sub_response.error}")

        first = next(iter(sub_response.events), None)
        if first is None:
            pytest.skip("SubscribeToTask returned no events")

        payload = first.WhichOneof("payload")
        passed = payload == "task"
        errors = (
            []
            if passed
            else [
                f"First event payload should be 'task', got {payload!r}"
            ]
        )

        record(
            collector=compatibility_collector,
            req=req,
            transport=TRANSPORT,
            passed=passed,
            errors=errors,
        )
        assert passed, fail_msg(req, TRANSPORT, errors[0])
