"""Shared helpers for creating tasks across transports.

Many conformance tests need a real task to exist before they can exercise
an operation (GetTask, CancelTask, multi-turn, push notifications, …).
This module provides transport-agnostic factory functions that call
``send_message`` and return the resulting task/context IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import (
    TASK_STATE_COMPLETED,
    TASK_STATE_INPUT_REQUIRED,
    tck_id,
)
from tck.validators.payload import validate_task_state


if TYPE_CHECKING:
    from tck.requirements.base import TaskStateBinding
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass
class TaskInfo:
    """Identifiers extracted from a successful SendMessage response."""

    task_id: str
    context_id: str | None
    transport: str


def create_completed_task(client: BaseTransportClient) -> TaskInfo:
    """Create a task that reaches a terminal (completed) state.

    Uses the ``tck-complete-task`` prefix which maps to a SUT scenario that
    immediately completes the task.

    Calls ``pytest.skip`` if the task cannot be created or does not reach
    the expected state.
    """
    return _send_and_validate(client, prefix="complete-task", expected_state=TASK_STATE_COMPLETED)


def create_working_task(client: BaseTransportClient) -> TaskInfo:
    """Create a task that stays in a non-terminal (input_required) state.

    Uses the ``tck-input-required`` prefix which maps to a SUT scenario that
    sets the task status to ``input_required`` instead of completing it.

    Calls ``pytest.skip`` if the task cannot be created or does not reach
    the expected state.
    """
    return _send_and_validate(client, prefix="input-required", expected_state=TASK_STATE_INPUT_REQUIRED)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _send_and_validate(
    client: BaseTransportClient,
    *,
    prefix: str,
    expected_state: TaskStateBinding,
) -> TaskInfo:
    """Send a message and validate the resulting task state.

    Calls ``pytest.skip`` if the task cannot be created or the state
    does not match *expected_state*.
    """
    message: dict[str, Any] = {
        "role": "ROLE_USER",
        "parts": [{"text": "TCK prerequisite task creation"}],
        "messageId": tck_id(prefix),
    }
    response = client.send_message(message=message)
    if not response.success:
        pytest.skip(f"send_message failed: {response.error}")

    task_id = response.task_id
    if not task_id:
        pytest.skip("Could not extract task ID from send_message response")

    errors = validate_task_state(response, response.transport, expected_state)
    if errors:
        pytest.skip(errors[0])

    return TaskInfo(
        task_id=task_id,
        context_id=response.context_id,
        transport=response.transport,
    )
