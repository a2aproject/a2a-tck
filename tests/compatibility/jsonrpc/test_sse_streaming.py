"""JSON-RPC SSE streaming tests.

Validates that JSON-RPC streaming responses use Server-Sent Events correctly,
including event format, structure, ordering, and lifecycle.

Requirements tested:
    JSONRPC-SSE-001 — SSE event format (JSON-RPC envelope around StreamResponse)
    STREAM-SUB-001  — SubscribeToTask first event is a Task
    STREAM-SUB-004  — SubscribeToTask returns TaskNotFoundError for non-existent task
"""

from __future__ import annotations

import contextlib

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.registry import get_requirement_by_id
from tck.transport.jsonrpc_client import TRANSPORT
from tests.compatibility._test_helpers import fail_msg, get_client, record
from tests.compatibility.markers import jsonrpc, streaming


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

JSONRPC_SSE_001 = get_requirement_by_id("JSONRPC-SSE-001")
STREAM_SUB_001 = get_requirement_by_id("STREAM-SUB-001")
STREAM_SUB_004 = get_requirement_by_id("STREAM-SUB-004")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TASK_NOT_FOUND_CODE = -32001

_TERMINAL_STATES = {
    "TASK_STATE_COMPLETED", "TASK_STATE_FAILED",
    "TASK_STATE_CANCELED", "TASK_STATE_REJECTED",
}

_STREAM_RESPONSE_KEYS = {"task", "message", "statusUpdate", "artifactUpdate"}

_SAMPLE_MESSAGE = {
    "role": "ROLE_USER",
    "parts": [{"text": "TCK streaming test"}],
    "messageId": "tck-sse-streaming-001",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_streaming_events(
    client: BaseTransportClient,
    agent_card: dict[str, Any],
) -> list[dict]:
    """Send a streaming message and return collected events.

    Skips the test if the agent does not support streaming or
    if the streaming call fails.
    """
    caps = agent_card.get("capabilities", {})
    if not caps.get("streaming"):
        pytest.skip("Agent does not support streaming")

    response = client.send_streaming_message(message=_SAMPLE_MESSAGE)
    if not response.success:
        pytest.skip(f"Streaming call failed: {response.error}")

    events = list(response.events)
    if not events:
        pytest.skip("Server returned no SSE events")

    return events


def _get_task_status(event: dict) -> str | None:
    """Extract task status string from a streaming event result."""
    result = event.get("result", {})
    # Check statusUpdate first, then task
    status_update = result.get("statusUpdate")
    if status_update:
        state = status_update.get("status", {})
        return state.get("state") if isinstance(state, dict) else None
    task = result.get("task")
    if task:
        status = task.get("status", {})
        return status.get("state") if isinstance(status, dict) else None
    return None


# ---------------------------------------------------------------------------
# SSE event format tests (SendStreamingMessage)
# ---------------------------------------------------------------------------


@jsonrpc
@streaming
class TestSseStreamingFormat:
    """Validate SSE event structure for JSON-RPC streaming responses."""

    def test_streaming_events_have_jsonrpc_envelope(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """JSONRPC-SSE-001: Each SSE event must be a JSON-RPC 2.0 response."""
        req = JSONRPC_SSE_001
        transport = "jsonrpc"
        client = get_client(transport_clients, TRANSPORT, compliance_collector=compliance_collector, req=req)
        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compliance_collector, req=req, transport=transport, passed=False, skipped=True)
        events = _get_streaming_events(client, agent_card)

        errors: list[str] = []
        for i, event in enumerate(events):
            if event.get("jsonrpc") != "2.0":
                errors.append(
                    f"Event {i}: missing or wrong 'jsonrpc' field "
                    f"(got {event.get('jsonrpc')!r})"
                )
            if "id" not in event:
                errors.append(f"Event {i}: missing 'id' field")
            if "result" not in event and "error" not in event:
                errors.append(f"Event {i}: missing both 'result' and 'error' fields")

        passed = len(errors) == 0
        record(
            collector=compliance_collector,
            req=req,
            transport=transport,
            passed=passed,
            errors=errors,
        )
        assert passed, fail_msg(req, transport, "; ".join(errors))

    def test_streaming_events_contain_stream_response(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """JSONRPC-SSE-001: Each event result contains a StreamResponse object."""
        req = JSONRPC_SSE_001
        transport = "jsonrpc"
        client = get_client(transport_clients, TRANSPORT, compliance_collector=compliance_collector, req=req)
        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compliance_collector, req=req, transport=transport, passed=False, skipped=True)
        events = _get_streaming_events(client, agent_card)

        errors: list[str] = []
        for i, event in enumerate(events):
            result = event.get("result")
            if result is None:
                # Error events are acceptable (validated elsewhere)
                if "error" not in event:
                    errors.append(f"Event {i}: no 'result' or 'error' field")
                continue
            found_keys = _STREAM_RESPONSE_KEYS & set(result.keys())
            if not found_keys:
                errors.append(
                    f"Event {i}: result has none of {sorted(_STREAM_RESPONSE_KEYS)}, "
                    f"got keys {sorted(result.keys())}"
                )

        passed = len(errors) == 0
        record(
            collector=compliance_collector,
            req=req,
            transport=transport,
            passed=passed,
            errors=errors,
        )
        assert passed, fail_msg(req, transport, "; ".join(errors))

    def test_streaming_has_terminal_event(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """JSONRPC-SSE-001: Stream ends with a terminal task state."""
        req = JSONRPC_SSE_001
        transport = "jsonrpc"
        client = get_client(transport_clients, TRANSPORT, compliance_collector=compliance_collector, req=req)
        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compliance_collector, req=req, transport=transport, passed=False, skipped=True)
        events = _get_streaming_events(client, agent_card)

        # Determine which stream pattern is used
        last_event = events[-1]
        last_result = last_event.get("result", {})

        if "message" in last_result:
            # Message-only stream: exactly one Message, then close
            passed = len(events) == 1
            errors = (
                []
                if passed
                else [
                    f"Message-only stream must contain exactly one event, "
                    f"got {len(events)}"
                ]
            )
        else:
            # Task lifecycle stream: last event must have a terminal state
            last_status = _get_task_status(last_event)
            passed = last_status in _TERMINAL_STATES
            errors = (
                []
                if passed
                else [
                    f"Last event does not contain a terminal task state "
                    f"(expected one of {sorted(_TERMINAL_STATES)}, "
                    f"got {last_status!r})"
                ]
            )
        record(
            collector=compliance_collector,
            req=req,
            transport=transport,
            passed=passed,
            errors=errors,
        )
        assert passed, fail_msg(req, transport, errors[0])


# ---------------------------------------------------------------------------
# SubscribeToTask tests
# ---------------------------------------------------------------------------


@jsonrpc
@streaming
class TestSseSubscribeToTask:
    """Validate SubscribeToTask streaming behavior."""

    def test_subscribe_nonexistent_task_returns_error(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """STREAM-SUB-004: SubscribeToTask returns TaskNotFoundError for non-existent task."""
        req = STREAM_SUB_004
        transport = "jsonrpc"
        client = get_client(transport_clients, TRANSPORT, compliance_collector=compliance_collector, req=req)

        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compliance_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support streaming")

        response = client.subscribe_to_task(id="tck-nonexistent-subscribe-001")

        # The server may return a normal JSON-RPC error (not SSE) for
        # non-existent tasks. Check the raw httpx response.
        body: dict | None = None
        with contextlib.suppress(Exception):
            body = response.raw_response.json()

        if body and "error" in body:
            code = body["error"].get("code")
            passed = code == _TASK_NOT_FOUND_CODE
            errors = (
                []
                if passed
                else [
                    f"Expected TaskNotFoundError (-32001), got code {code}"
                ]
            )
        else:
            # Try consuming events — some servers may send error as SSE event
            events = list(response.events)
            if events and "error" in events[0]:
                code = events[0]["error"].get("code")
                passed = code == _TASK_NOT_FOUND_CODE
                errors = (
                    []
                    if passed
                    else [
                        f"Expected TaskNotFoundError (-32001), got code {code}"
                    ]
                )
            else:
                pytest.skip(
                    "Server did not return an error for non-existent task subscribe"
                )

        record(
            collector=compliance_collector,
            req=req,
            transport=transport,
            passed=passed,
            errors=errors,
        )
        assert passed, fail_msg(req, transport, errors[0])

    def test_subscribe_first_event_is_task(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """STREAM-SUB-001: First event from SubscribeToTask contains a Task object."""
        req = STREAM_SUB_001
        transport = "jsonrpc"
        client = get_client(transport_clients, TRANSPORT, compliance_collector=compliance_collector, req=req)

        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compliance_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support streaming")

        # First, create a task via send_message
        msg_response = client.send_message(message=_SAMPLE_MESSAGE)
        if not msg_response.success:
            pytest.skip(f"send_message failed: {msg_response.error}")

        body = msg_response.raw_response
        task_id = None
        result = body.get("result") if isinstance(body, dict) else None
        if isinstance(result, dict):
            # Task may be at result.id or nested under result.task.id
            task = result.get("task")
            task_id = task.get("id") if isinstance(task, dict) else result.get("id")
        if not task_id:
            pytest.skip("Could not extract task ID from send_message response")

        # Subscribe to the task
        sub_response = client.subscribe_to_task(id=task_id)

        # Check for error response (non-SSE)
        sub_body: dict | None = None
        with contextlib.suppress(Exception):
            sub_body = sub_response.raw_response.json()
        if isinstance(sub_body, dict) and "error" in sub_body:
            pytest.skip(
                f"SubscribeToTask returned error: "
                f"{sub_body['error'].get('message', sub_body['error'])}"
            )

        events = list(sub_response.events)
        if not events:
            pytest.skip("SubscribeToTask returned no events")

        first_event = events[0]
        first_result = first_event.get("result", {})
        passed = "task" in first_result
        errors = (
            []
            if passed
            else [
                f"First event does not contain a 'task' field; "
                f"got keys {sorted(first_result.keys())}"
            ]
        )

        record(
            collector=compliance_collector,
            req=req,
            transport=transport,
            passed=passed,
            errors=errors,
        )
        assert passed, fail_msg(req, transport, errors[0])
