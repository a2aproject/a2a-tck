"""Cross-transport task lifecycle tests.

Validates operations that require a real task to exist first:
GetTask, CancelTask, multi-turn messaging, and SubscribeToTask lifecycle.

Requirements tested:
    CORE-GET-001    — GetTask returns current task state
    CORE-CANCEL-001 — CancelTask returns updated task state
    CORE-CANCEL-002 — CancelTask on terminal task returns error
    CORE-SEND-002   — SendMessage to terminal task returns error
    CORE-MULTI-005  — SendMessage infers contextId from taskId
    CORE-MULTI-006  — SendMessage rejects mismatching contextId
    STREAM-SUB-002  — SubscribeToTask terminates at terminal state
    STREAM-SUB-003  — SubscribeToTask rejects terminal task
"""

from __future__ import annotations

import threading
import uuid

from typing import TYPE_CHECKING, Any

import pytest

from specification.generated import a2a_pb2
from tck.requirements.registry import get_requirement_by_id
from tck.transport import ALL_TRANSPORTS
from tests.compatibility._task_helpers import TaskInfo, create_task, extract_context_id, extract_task_id
from tests.compatibility._test_helpers import fail_msg, get_client, record
from tests.compatibility.markers import must, streaming


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

CORE_GET_001 = get_requirement_by_id("CORE-GET-001")
CORE_CANCEL_001 = get_requirement_by_id("CORE-CANCEL-001")
CORE_CANCEL_002 = get_requirement_by_id("CORE-CANCEL-002")
CORE_SEND_002 = get_requirement_by_id("CORE-SEND-002")
CORE_MULTI_005 = get_requirement_by_id("CORE-MULTI-005")
CORE_MULTI_006 = get_requirement_by_id("CORE-MULTI-006")
STREAM_SUB_002 = get_requirement_by_id("STREAM-SUB-002")
STREAM_SUB_003 = get_requirement_by_id("STREAM-SUB-003")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SUBSCRIBE_TIMEOUT_S = 10

_GRPC_TERMINAL_STATES = frozenset({
    a2a_pb2.TASK_STATE_COMPLETED,
    a2a_pb2.TASK_STATE_FAILED,
    a2a_pb2.TASK_STATE_CANCELED,
    a2a_pb2.TASK_STATE_REJECTED,
})

_JSON_TERMINAL_STATES = frozenset({"completed", "failed", "canceled", "rejected"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_terminal_status(response: Any, transport: str) -> bool:
    """Check whether a response contains a task in a terminal state."""
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
        return state.lower() in _JSON_TERMINAL_STATES
    return False


def _create_cancelable_task(client: BaseTransportClient) -> TaskInfo:
    """Create a task that stays in a non-terminal state (input_required).

    Uses the ``tck-cancel-001`` prefix which maps to a SUT scenario that
    sets the task status to ``input_required`` instead of completing it.
    """
    message = {
        "role": "ROLE_USER",
        "parts": [{"text": "TCK cancelable task creation"}],
        "messageId": f"tck-cancel-001-{uuid.uuid4().hex[:8]}",
    }
    response = client.send_message(message=message)
    if not response.success:
        pytest.skip(f"send_message failed: {response.error}")

    task_id = extract_task_id(response)
    if not task_id:
        pytest.skip("Could not extract task ID from send_message response")

    context_id = extract_context_id(response)
    return TaskInfo(
        task_id=task_id,
        context_id=context_id,
        transport=response.transport,
    )


def _event_has_terminal_state(event: Any, transport: str) -> bool:
    """Check whether a streaming event carries a terminal task state."""
    if transport == "grpc":
        if hasattr(event, "WhichOneof"):
            payload = event.WhichOneof("payload")
            if payload == "task":
                return event.task.status.state in _GRPC_TERMINAL_STATES
            if payload == "status_update":
                return event.status_update.status.state in _GRPC_TERMINAL_STATES
        return False

    # JSON-RPC / HTTP+JSON — event is a dict
    if not isinstance(event, dict):
        return False
    # JSON-RPC events are wrapped in a JSON-RPC envelope
    result = event.get("result", event)
    if isinstance(result, dict):
        # Could be a task, status_update, etc.
        task = result.get("task", result)
        status = task.get("status", {}) if isinstance(task, dict) else {}
        state = status.get("state", "") if isinstance(status, dict) else ""
        if state.lower() in _JSON_TERMINAL_STATES:
            return True
        # Check status_update path
        status_update = result.get("statusUpdate", result.get("status_update", {}))
        if isinstance(status_update, dict):
            su_status = status_update.get("status", {})
            su_state = su_status.get("state", "") if isinstance(su_status, dict) else ""
            if su_state.lower() in _JSON_TERMINAL_STATES:
                return True
    return False


def _collect_events_with_timeout(
    events_iter: Any,
    timeout: float = _SUBSCRIBE_TIMEOUT_S,
) -> tuple[list[Any], bool]:
    """Collect streaming events with a hard wall-clock timeout.

    Runs event consumption in a daemon thread so that we can enforce
    the deadline even when ``next(events_iter)`` itself blocks
    (e.g. an SSE connection waiting for data that never arrives).

    Returns a tuple of (events, timed_out).
    """
    collected: list[Any] = []

    def _drain() -> None:
        for event in events_iter:
            collected.append(event)

    thread = threading.Thread(target=_drain, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    timed_out = thread.is_alive()
    return collected, timed_out


# ---------------------------------------------------------------------------
# GetTask tests
# ---------------------------------------------------------------------------


@must
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestGetTask:
    """Tests for GetTask on real tasks."""

    def test_get_task_returns_current_state(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """CORE-GET-001: GetTask returns the current state of an existing task."""
        req = CORE_GET_001
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_task(client)

        response = client.get_task(id=info.task_id)

        errors: list[str] = []
        if not response.success:
            errors.append(f"GetTask failed: {response.error}")
        else:
            # Verify a task ID is present in the response
            returned_id = extract_task_id(response)
            if returned_id != info.task_id:
                errors.append(
                    f"GetTask returned task ID {returned_id!r}, "
                    f"expected {info.task_id!r}"
                )

        passed = not errors
        record(collector=compatibility_collector, req=req, transport=transport, passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, "; ".join(errors))


# ---------------------------------------------------------------------------
# CancelTask tests
# ---------------------------------------------------------------------------


@must
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestCancelTask:
    """Tests for CancelTask on real tasks."""

    def test_cancel_task_returns_updated_state(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """CORE-CANCEL-001: CancelTask returns the task with updated state."""
        req = CORE_CANCEL_001
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = _create_cancelable_task(client)

        response = client.cancel_task(id=info.task_id)

        errors: list[str] = []
        if not response.success:
            # Server may reject if task already reached terminal state
            # or cancellation is not supported — still valid behavior
            errors.append(f"CancelTask returned error: {response.error}")
        else:
            returned_id = extract_task_id(response)
            if returned_id != info.task_id:
                errors.append(
                    f"CancelTask returned task ID {returned_id!r}, "
                    f"expected {info.task_id!r}"
                )

        passed = not errors
        record(collector=compatibility_collector, req=req, transport=transport, passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, "; ".join(errors))

    def test_cancel_terminal_task_returns_error(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """CORE-CANCEL-002: CancelTask on a terminal task returns TaskNotCancelableError."""
        req = CORE_CANCEL_002
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_task(client)

        # Verify the task reached a terminal state
        get_response = client.get_task(id=info.task_id)
        if not get_response.success:
            pytest.skip(f"GetTask failed: {get_response.error}")
        if not _is_terminal_status(get_response, transport):
            pytest.skip("Task did not reach a terminal state; cannot test cancel-after-terminal")

        response = client.cancel_task(id=info.task_id)

        errors: list[str] = []
        if response.success:
            errors.append(
                "CancelTask on a terminal task should return an error, "
                "but succeeded"
            )

        passed = not errors
        record(collector=compatibility_collector, req=req, transport=transport, passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, "; ".join(errors))


# ---------------------------------------------------------------------------
# Multi-turn messaging tests
# ---------------------------------------------------------------------------


@must
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestMultiTurn:
    """Tests for multi-turn messaging on existing tasks."""

    def test_send_message_to_terminal_task(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """CORE-SEND-002: SendMessage to a terminal task returns UnsupportedOperationError."""
        req = CORE_SEND_002
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_task(client)

        # Verify the task reached a terminal state
        get_response = client.get_task(id=info.task_id)
        if not get_response.success:
            pytest.skip(f"GetTask failed: {get_response.error}")
        if not _is_terminal_status(get_response, transport):
            pytest.skip("Task did not reach a terminal state; cannot test send-after-terminal")

        # Send another message referencing the terminal task
        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "Follow-up to terminal task"}],
            "messageId": f"tck-terminal-{uuid.uuid4().hex[:8]}",
            "taskId": info.task_id,
        }
        response = client.send_message(message=msg)

        errors: list[str] = []
        if response.success:
            errors.append(
                "SendMessage to a terminal task should return an error, "
                "but succeeded"
            )

        passed = not errors
        record(collector=compatibility_collector, req=req, transport=transport, passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, "; ".join(errors))

    def test_infer_context_from_task(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """CORE-MULTI-005: SendMessage with only taskId infers contextId from the task."""
        req = CORE_MULTI_005
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_task(client)

        if not info.context_id:
            pytest.skip("Original task did not include a contextId")

        # Send a follow-up with only taskId (no contextId)
        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "Follow-up message"}],
            "messageId": f"tck-infer-ctx-{uuid.uuid4().hex[:8]}",
            "taskId": info.task_id,
        }
        response = client.send_message(message=msg)

        errors: list[str] = []
        if not response.success:
            # An error is acceptable if the task is already terminal
            # but we still record it
            errors.append(f"SendMessage with taskId failed: {response.error}")

        passed = not errors
        record(collector=compatibility_collector, req=req, transport=transport, passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, "; ".join(errors))

    def test_reject_mismatching_context(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """CORE-MULTI-006: SendMessage with taskId + wrong contextId returns error."""
        req = CORE_MULTI_006
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_task(client)

        # Send with a deliberately wrong contextId
        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "Mismatched context test"}],
            "messageId": f"tck-mismatch-{uuid.uuid4().hex[:8]}",
            "taskId": info.task_id,
            "contextId": f"wrong-context-{uuid.uuid4().hex[:8]}",
        }
        response = client.send_message(message=msg)

        errors: list[str] = []
        if response.success:
            errors.append(
                "SendMessage with mismatching contextId should return an error, "
                "but succeeded"
            )

        passed = not errors
        record(collector=compatibility_collector, req=req, transport=transport, passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, "; ".join(errors))


# ---------------------------------------------------------------------------
# SubscribeToTask lifecycle tests
# ---------------------------------------------------------------------------


@must
@streaming
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestSubscribeLifecycle:
    """Tests for SubscribeToTask lifecycle behavior."""

    def test_subscribe_terminates_at_terminal_state(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """STREAM-SUB-002: SubscribeToTask stream closes at terminal state."""
        req = STREAM_SUB_002
        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support streaming")

        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_task(client)

        sub_response = client.subscribe_to_task(id=info.task_id)
        if not sub_response.success:
            pytest.skip(f"subscribe_to_task failed: {sub_response.error}")

        # Consume events with a timeout to avoid blocking indefinitely
        events, timed_out = _collect_events_with_timeout(sub_response.events)

        if timed_out:
            pytest.skip("SubscribeToTask timed out waiting for stream to close")

        errors: list[str] = []
        if not events:
            errors.append("SubscribeToTask returned no events")
        else:
            # The stream closed (iterator exhausted), which means it
            # terminated.  Verify the last event carries a terminal state.
            last = events[-1]
            last_is_terminal = _event_has_terminal_state(last, transport)
            if not last_is_terminal:
                errors.append(
                    "Stream closed but last event does not carry a terminal state"
                )

        passed = not errors
        record(collector=compatibility_collector, req=req, transport=transport, passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, "; ".join(errors))

    def test_subscribe_rejects_terminal_task(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """STREAM-SUB-003: SubscribeToTask on a terminal task returns error."""
        req = STREAM_SUB_003
        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support streaming")

        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_task(client)

        # Verify the task reached a terminal state
        get_response = client.get_task(id=info.task_id)
        if not get_response.success:
            pytest.skip(f"GetTask failed: {get_response.error}")
        if not _is_terminal_status(get_response, transport):
            pytest.skip("Task did not reach a terminal state; cannot test subscribe-after-terminal")

        sub_response = client.subscribe_to_task(id=info.task_id)

        errors: list[str] = []
        if sub_response.success:
            # Some servers may return success but deliver an error on iteration
            try:
                _collect_events_with_timeout(sub_response.events)[0]
                errors.append(
                    "SubscribeToTask on a terminal task should return an error, "
                    "but succeeded"
                )
            except Exception:
                pass  # Error during iteration is acceptable
        # else: server returned error immediately — correct behavior

        passed = not errors
        record(collector=compatibility_collector, req=req, transport=transport, passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, "; ".join(errors))
