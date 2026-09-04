"""Cross-transport AUTH_REQUIRED lifecycle tests.

Validates the in-task authorization flow of section 7.6.1: when an agent
needs the client to satisfy an authorization request, it tracks the work
with a Task and moves that Task to ``auth_required`` rather than resolving
it.  A blocking ``send_message`` returns at that interrupted state.

The security-relevant assertion is the negative one.  ``auth_required`` is
NOT terminal, so an agent that answers an authorization-gated request with
a terminal state has reported an unauthorized operation as settled.  Each
test therefore checks terminality separately from state identity, so that
failure mode is named rather than folded into a generic mismatch.

Requirements tested:
    AUTH-INTASK-001 - Agent MUST use a Task to track an operation requiring
                      authorization.
    AUTH-INTASK-002 - Agent MUST transition the TaskState to
                      TASK_STATE_AUTH_REQUIRED.
    CORE-EXECUTION-MODE-001 - Blocking mode waits for a terminal or
                      interrupted state (input_required, auth_required)
                      before returning.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import (
    TASK_STATE_AUTH_REQUIRED,
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

AUTH_INTASK_001 = get_requirement_by_id("AUTH-INTASK-001")

AUTH_INTASK_002 = get_requirement_by_id("AUTH-INTASK-002")

CORE_EXECUTION_MODE_001 = get_requirement_by_id("CORE-EXECUTION-MODE-001")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GRPC_TERMINAL_STATES = frozenset(s.grpc_value for s in TERMINAL_STATES)

_JSON_TERMINAL_STATES = frozenset(s.json_value for s in TERMINAL_STATES)

_GRPC_AUTH_REQUIRED = TASK_STATE_AUTH_REQUIRED.grpc_value

_JSON_AUTH_REQUIRED = TASK_STATE_AUTH_REQUIRED.json_value


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task_state(response: Any, transport: str) -> Any:
    """Extract the task state from a response, or ``None`` if absent.

    Returns the raw state value (a gRPC enum int or a ProtoJSON enum name)
    so callers can compare against either the terminal set or the
    auth_required binding.
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


def _is_auth_required_status(response: Any, transport: str) -> bool:
    """Check whether a response contains a task in the auth_required state."""
    state = _task_state(response, transport)
    if state is None:
        return False
    if transport == "grpc":
        return state == _GRPC_AUTH_REQUIRED
    return state == _JSON_AUTH_REQUIRED


def _is_message_response(response: Any, transport: str) -> bool:
    """Return True when a successful, task-less response is a bare Message.

    AUTH-INTASK-001 requires the agent to track an authorization-gated
    operation with a Task.  A successful ``send_message`` that answers with a
    Message instead is the exact violation these tests exist to catch, so it
    must be distinguished from a response whose shape the client simply could
    not parse.  A recognized Message shape returns True (the caller fails);
    anything unrecognized returns False (the caller skips, since there is
    nothing to assert on).
    """
    raw = response.raw_response
    if transport == "grpc":
        # SendMessageResponse.payload is a oneof of "task" or "message".
        try:
            return raw.WhichOneof("payload") == "message"
        except (ValueError, AttributeError):
            return False

    # JSON-RPC or HTTP+JSON
    if not isinstance(raw, dict):
        return False
    result = raw.get("result") if transport == "jsonrpc" else raw
    if not isinstance(result, dict):
        return False
    # A Message may arrive directly as the result or under a "message" key.
    candidate = result.get("message", result)
    if not isinstance(candidate, dict):
        return False
    if candidate.get("kind") == "message":
        return True
    # No discriminator present: treat a Message-shaped object (messageId and
    # parts, without the Task-only id/status) as a bare Message.  Anything
    # else is an unrecognized shape and is left for the caller to skip.
    return (
        "messageId" in candidate
        and "parts" in candidate
        and "status" not in candidate
        and "id" not in candidate
    )


def _send_auth_required(
    client: BaseTransportClient,
    collector: Any,
    req: Any,
) -> Any:
    """Send the ``tck-auth-required`` message and return the raw response.

    Deliberately does NOT go through ``_task_helpers``: those factories call
    ``pytest.skip`` when the task does not reach the expected state, which
    would convert the exact failure these tests exist to catch -- an agent
    settling an authorization-gated operation instead of asking for
    authorization -- into a silent skip.

    A successful response that carries no task id is inspected rather than
    skipped: if it is a bare Message, the agent has answered an
    authorization-gated request without tracking it as a Task, which is the
    AUTH-INTASK-001 violation and is recorded as a failure.  Only a
    transport-level failure or a genuinely unrecognized payload shape skips,
    because those leave nothing to assert on.  The task state itself is
    always asserted by the caller.
    """
    transport = client.transport
    message: dict[str, Any] = {
        "role": "ROLE_USER",
        "parts": [{"text": "TCK auth-required task creation"}],
        "messageId": tck_id("auth-required"),
    }
    response = client.send_message(message=message)
    if not response.success:
        pytest.skip(f"send_message failed: {response.error}")
    if not response.task_id:
        if _is_message_response(response, transport):
            assert_and_record(
                collector,
                req,
                transport,
                [
                    "agent returned a bare Message where a Task is required "
                    "for in-task authorization"
                ],
            )
        pytest.skip("Could not extract task ID from send_message response")
    return response


# ---------------------------------------------------------------------------
# AUTH_REQUIRED lifecycle tests
# ---------------------------------------------------------------------------


@must
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestAuthRequiredLifecycle:
    """Tests for the auth_required interrupted-state lifecycle."""

    def test_authorization_request_is_tracked_by_a_task(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """AUTH-INTASK-001: authorization is tracked with a Task.

        An agent requesting authorization MUST track the operation with a
        Task rather than answering with a bare Message.  ``_send_auth_required``
        fails outright when the response is a bare Message and skips only on a
        genuinely unrecognized shape, so reaching this point means a Task id
        was returned; the assertion confirms it is retrievable by that id,
        which is what makes the authorization request addressable.
        """
        req = AUTH_INTASK_001
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        send_response = _send_auth_required(client, compatibility_collector, req)

        get_response = client.get_task(id=send_response.task_id)

        errors: list[str] = []
        if not get_response.success:
            errors.append(
                "Task tracking the authorization request could not be "
                f"retrieved by id: {get_response.error}"
            )
        elif _task_state(get_response, transport) is None:
            errors.append("Retrieved task carries no status.state")

        assert_and_record(compatibility_collector, req, transport, errors)

    def test_task_transitions_to_auth_required(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """AUTH-INTASK-002: the task moves to auth_required.

        The agent MUST transition the TaskState to TASK_STATE_AUTH_REQUIRED
        when it needs the client to satisfy an authorization request.

        Terminality is checked first and reported separately: a terminal
        state here means an authorization-gated operation was reported as
        settled without the authorization ever being supplied, which is a
        materially different (and worse) defect than landing in some other
        non-terminal state.
        """
        req = AUTH_INTASK_002
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        send_response = _send_auth_required(client, compatibility_collector, req)

        get_response = client.get_task(id=send_response.task_id)
        if not get_response.success:
            pytest.skip(f"GetTask failed: {get_response.error}")

        errors: list[str] = []
        if _is_terminal_status(get_response, transport):
            errors.append(
                "Task reached a terminal state while awaiting authorization; "
                "an unauthorized operation must not be reported as settled"
            )
        elif not _is_auth_required_status(get_response, transport):
            errors.append(
                "Task is not in the auth_required state after the agent "
                "requested authorization"
            )

        assert_and_record(compatibility_collector, req, transport, errors)

    def test_blocking_send_returns_auth_required(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """CORE-EXECUTION-MODE-001: blocking send returns auth_required.

        This covers the auth_required half of the interrupted-state rule;
        the input_required half is exercised in
        ``test_task_input_required.py``.  A blocking send_message (the
        default, ``return_immediately`` false or unset) that drives the SUT
        into auth_required MUST return once that interrupted state is
        reached, rather than blocking on to a terminal state.
        """
        req = CORE_EXECUTION_MODE_001
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        send_response = _send_auth_required(client, compatibility_collector, req)

        get_response = client.get_task(id=send_response.task_id)
        if not get_response.success:
            pytest.skip(f"GetTask failed: {get_response.error}")

        errors: list[str] = []
        if _is_terminal_status(get_response, transport):
            errors.append(
                "Blocking send_message returned a terminal state; "
                "expected the interrupted auth_required state"
            )
        elif not _is_auth_required_status(get_response, transport):
            errors.append(
                "Task is not in the auth_required state after a blocking "
                "send_message that requires authorization"
            )

        assert_and_record(compatibility_collector, req, transport, errors)
