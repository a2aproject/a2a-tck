"""Cross-transport INPUT_REQUIRED lifecycle tests.

Validates blocking send_message execution mode when a task reaches the
``input_required`` interrupted state.  A blocking request (the default,
``return_immediately`` false or unset) MUST wait until the task reaches a
terminal state or an interrupted state before returning.  These tests
cover both halves of that requirement for the ``input_required`` path:
the initial request that stops at ``input_required`` and the follow-up
request that continues such a task to a terminal state.

The lifecycle state is asserted on the send_message RESPONSE itself, not
on a later GetTask.  That is the tightest binding to the requirement: the
rule is about what a blocking send returns, so the returned state is the
direct evidence that the agent waited before returning rather than
answering early.  These tests deliberately do NOT route through the
``_task_helpers`` factories: those call ``pytest.skip`` when the task does
not reach the expected state, which would convert the exact failure these
tests exist to catch -- a blocking send answering with the wrong state --
into a silent skip.  Only a transport-level failure or a missing task id
skips here, because those leave nothing to assert on.

Requirements tested:
    CORE-EXECUTION-MODE-001 - Blocking mode waits for terminal or
                              interrupted state (input_required, auth_required)
                              before returning.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import (
    TASK_STATE_INPUT_REQUIRED,
    TERMINAL_STATES,
    tck_id,
)
from tck.requirements.registry import get_requirement_by_id
from tck.transport import ALL_TRANSPORTS
from tests.compatibility._test_helpers import assert_and_record, get_client
from tests.compatibility.markers import must


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

CORE_EXECUTION_MODE_001 = get_requirement_by_id("CORE-EXECUTION-MODE-001")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GRPC_TERMINAL_STATES = frozenset(s.grpc_value for s in TERMINAL_STATES)

_JSON_TERMINAL_STATES = frozenset(s.json_value for s in TERMINAL_STATES)

_GRPC_INPUT_REQUIRED = TASK_STATE_INPUT_REQUIRED.grpc_value

_JSON_INPUT_REQUIRED = TASK_STATE_INPUT_REQUIRED.json_value


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task_state(response: Any, transport: str) -> Any:
    """Extract the task state from a response, or ``None`` if absent.

    Mirrors the extraction in ``_is_terminal_status`` from
    ``test_task_lifecycle.py`` but returns the raw state value (a gRPC
    enum int or a ProtoJSON enum name) so callers can compare against
    either the terminal set or the input_required binding.  Handles both
    a SendMessage response (whose ``payload``/``result`` carries the task)
    and a bare Task proto or dict.
    """
    raw = response.raw_response
    if transport == "grpc":
        # SendMessageResponse has a "payload" oneof; Task proto does not.
        try:
            payload = raw.WhichOneof("payload")
            if payload == "task":
                return raw.task.status.state
        except (ValueError, AttributeError):
            pass
        # Task proto returned directly (GetTask, CancelTask)
        if hasattr(raw, "status"):
            return raw.status.state
        return None

    # JSON-RPC or HTTP+JSON
    if not isinstance(raw, dict):
        return None
    if transport == "jsonrpc":
        result = raw.get("result", {})
        task = result.get("task", result) if isinstance(result, dict) else {}
    else:
        task = raw.get("task", raw)

    if isinstance(task, dict):
        status = task.get("status", {})
        return status.get("state", "") if isinstance(status, dict) else ""
    return None


def _is_terminal_status(response: Any, transport: str) -> bool:
    """Check whether a response contains a task in a terminal state."""
    state = _task_state(response, transport)
    if state is None:
        return False
    if transport == "grpc":
        return state in _GRPC_TERMINAL_STATES
    return state in _JSON_TERMINAL_STATES


def _is_input_required_status(response: Any, transport: str) -> bool:
    """Check whether a response contains a task in the input_required state."""
    state = _task_state(response, transport)
    if state is None:
        return False
    if transport == "grpc":
        return state == _GRPC_INPUT_REQUIRED
    return state == _JSON_INPUT_REQUIRED


def _send_input_required(client: BaseTransportClient) -> Any:
    """Send the ``tck-input-required`` message and return the raw response.

    Deliberately does NOT go through ``_task_helpers``: those factories call
    ``pytest.skip`` when the task does not reach the expected state, which
    would convert the exact failure these tests exist to catch -- a blocking
    send answering with the wrong state -- into a silent skip.  Only a
    transport-level failure or a missing task id skips here, because those
    leave nothing to assert on.  The task state itself is always asserted by
    the caller.
    """
    message: dict[str, Any] = {
        "role": "ROLE_USER",
        "parts": [{"text": "TCK input-required task creation"}],
        "messageId": tck_id("input-required"),
    }
    response = client.send_message(message=message)
    if not response.success:
        pytest.skip(f"send_message failed: {response.error}")
    if not response.task_id:
        pytest.skip("Could not extract task ID from send_message response")
    return response


def _send_completion_followup(client: BaseTransportClient, task_id: str) -> Any:
    """Send a completing follow-up on *task_id* and return the raw response.

    Same skip discipline as :func:`_send_input_required`: only a
    transport-level failure skips, so a follow-up that returns a
    non-terminal state -- the failure this continuation test exists to
    catch -- reaches the caller's assertion rather than being masked.
    """
    followup: dict[str, Any] = {
        "role": "ROLE_USER",
        "parts": [{"text": "TCK follow-up completion"}],
        "messageId": tck_id("complete-task"),
        "taskId": task_id,
    }
    response = client.send_message(message=followup)
    if not response.success:
        pytest.skip(f"Follow-up send_message failed: {response.error}")
    return response


# ---------------------------------------------------------------------------
# INPUT_REQUIRED lifecycle tests
# ---------------------------------------------------------------------------


@must
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestInputRequiredLifecycle:
    """Tests for the input_required interrupted-state lifecycle."""

    def test_blocking_send_returns_input_required(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """CORE-EXECUTION-MODE-001: blocking send returns input_required.

        A blocking send_message that drives the SUT into input_required
        waits and returns with the task in the input_required interrupted
        state, not a terminal state.

        Terminality is checked first and reported separately: a terminal
        state here means the blocking send answered early, reporting a task
        that still needs client input as settled, which is a materially
        different defect than landing in some other non-terminal state.
        The assertion is on the send RESPONSE, the tightest binding to
        "the agent waits before returning".
        """
        req = CORE_EXECUTION_MODE_001
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        send_response = _send_input_required(client)

        errors: list[str] = []
        if _is_terminal_status(send_response, transport):
            errors.append(
                "Blocking send_message returned a terminal state; "
                "expected the interrupted input_required state"
            )
        elif not _is_input_required_status(send_response, transport):
            errors.append(
                "Blocking send_message response is not in the input_required "
                "state after a send that requires input"
            )

        assert_and_record(compatibility_collector, req, transport, errors)

    def test_blocking_continuation_reaches_terminal(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """CORE-EXECUTION-MODE-001: blocking continuation reaches terminal.

        A follow-up blocking send_message that continues an input_required
        task waits until the task reaches a terminal state before
        returning.

        The initial send establishes an input_required task; the follow-up
        completes it.  The terminal state is asserted on the follow-up send
        RESPONSE, so a SUT whose blocking follow-up returns a non-terminal
        state -- answering before the work is done -- fails here rather than
        being skipped by a setup helper.
        """
        req = CORE_EXECUTION_MODE_001
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        send_response = _send_input_required(client)
        followup_response = _send_completion_followup(client, send_response.task_id)

        errors: list[str] = []
        if not _is_terminal_status(followup_response, transport):
            errors.append(
                "Blocking follow-up send_message on an input_required task "
                "did not reach a terminal state before returning"
            )

        assert_and_record(compatibility_collector, req, transport, errors)
