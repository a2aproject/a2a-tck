"""Cross-transport INPUT_REQUIRED lifecycle tests.

Validates blocking send_message execution mode when a task reaches the
``input_required`` interrupted state.  A blocking request (the default,
``return_immediately`` false or unset) MUST wait until the task reaches a
terminal state or an interrupted state before returning.  These tests
cover both halves of that requirement for the ``input_required`` path:
the initial request that stops at ``input_required`` and the follow-up
request that continues such a task to a terminal state.

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
)
from tck.requirements.registry import get_requirement_by_id
from tck.transport import ALL_TRANSPORTS
from tests.compatibility._task_helpers import create_multiturn_task, create_working_task
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
    either the terminal set or the input_required binding.
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

        ``create_working_task`` issues a default (blocking) send_message
        that the SUT answers by requiring input.  The task must therefore
        settle in input_required, which is an interrupted, NON-terminal
        state.
        """
        req = CORE_EXECUTION_MODE_001
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_working_task(client)

        get_response = client.get_task(id=info.task_id)
        if not get_response.success:
            pytest.skip(f"GetTask failed: {get_response.error}")

        errors: list[str] = []
        if _is_terminal_status(get_response, transport):
            errors.append(
                "Blocking send_message returned a terminal state; "
                "expected the interrupted input_required state"
            )
        elif not _is_input_required_status(get_response, transport):
            errors.append(
                "Task is not in the input_required state after a blocking "
                "send_message that requires input"
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

        ``create_multiturn_task`` first drives the task to input_required,
        then sends a completing follow-up.  After the blocking follow-up
        returns, the task must be in a terminal state.
        """
        req = CORE_EXECUTION_MODE_001
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_multiturn_task(client)

        get_response = client.get_task(id=info.task_id)
        if not get_response.success:
            pytest.skip(f"GetTask failed: {get_response.error}")

        errors: list[str] = []
        if not _is_terminal_status(get_response, transport):
            errors.append(
                "Blocking follow-up send_message on an input_required task "
                "did not reach a terminal state before returning"
            )

        assert_and_record(compatibility_collector, req, transport, errors)
