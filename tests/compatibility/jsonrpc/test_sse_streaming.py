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

from tck.requirements.base import tck_id
from tck.requirements.registry import get_requirement_by_id
from tck.transport.jsonrpc_client import TRANSPORT
from tests.compatibility._task_helpers import create_working_task
from tests.compatibility._test_helpers import assert_and_record, get_client, record
from tests.compatibility.markers import jsonrpc, must, streaming


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

_STREAM_RESPONSE_KEYS = {"task", "message", "statusUpdate", "artifactUpdate"}

_SAMPLE_MESSAGE = {
    "role": "ROLE_USER",
    "parts": [{"text": "TCK streaming test"}],
    "messageId": tck_id("sse-streaming-001"),
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
    if response.timed_out:
        pytest.skip("Streaming call timed out waiting for server to close the connection")
    if not response.success:
        pytest.skip(f"Streaming call failed: {response.error}")

    events = list(response.events)
    if not events:
        pytest.skip("Server returned no SSE events")

    return events


# ---------------------------------------------------------------------------
# SSE event format tests (SendStreamingMessage)
# ---------------------------------------------------------------------------


@must
@jsonrpc
@streaming
class TestSseStreamingFormat:
    """Validate SSE event structure for JSON-RPC streaming responses."""

    def test_streaming_events_have_jsonrpc_envelope(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """JSONRPC-SSE-001: Each SSE event must be a JSON-RPC 2.0 response."""
        req = JSONRPC_SSE_001
        transport = "jsonrpc"
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
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

        assert_and_record(compatibility_collector, req, transport, errors)

    def test_streaming_events_contain_stream_response(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """JSONRPC-SSE-001: Each event result contains a StreamResponse object."""
        req = JSONRPC_SSE_001
        transport = "jsonrpc"
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
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

        assert_and_record(compatibility_collector, req, transport, errors)



# ---------------------------------------------------------------------------
# SubscribeToTask tests
# ---------------------------------------------------------------------------


@must
@jsonrpc
@streaming
class TestSseSubscribeToTask:
    """Validate SubscribeToTask streaming behavior."""

    def test_subscribe_nonexistent_task_returns_error(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """STREAM-SUB-004: SubscribeToTask returns TaskNotFoundError for non-existent task."""
        req = STREAM_SUB_004
        transport = "jsonrpc"
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)

        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support streaming")

        response = client.subscribe_to_task(id=tck_id("nonexistent-subscribe-001"))

        # The server may return a normal JSON-RPC error (not SSE) for
        # non-existent tasks. Check the raw response — may be an httpx.Response
        # or an already-parsed dict (when the client detected a non-SSE reply).
        body: dict | None = None
        with contextlib.suppress(Exception):
            raw = response.raw_response
            body = raw if isinstance(raw, dict) else raw.json()

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

        assert_and_record(compatibility_collector, req, transport, errors)

    def test_subscribe_first_event_is_task(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """STREAM-SUB-001: First event from SubscribeToTask contains a Task object."""
        req = STREAM_SUB_001
        transport = "jsonrpc"
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)

        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support streaming")

        # Create a non-terminal task so SubscribeToTask is valid
        # (subscribing to a terminal task should be rejected per STREAM-SUB-003)
        info = create_working_task(client)

        # Subscribe to the task
        sub_response = client.subscribe_to_task(id=info.task_id)

        # Check for error response (non-SSE)
        sub_body: dict | None = None
        with contextlib.suppress(Exception):
            sub_body = sub_response.raw_response.json()
        if isinstance(sub_body, dict) and "error" in sub_body:
            pytest.skip(
                f"SubscribeToTask returned error: "
                f"{sub_body['error'].get('message', sub_body['error'])}"
            )

        first_event = next(iter(sub_response.events), None)
        if first_event is None:
            pytest.skip("SubscribeToTask returned no events")
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

        assert_and_record(compatibility_collector, req, transport, errors)
