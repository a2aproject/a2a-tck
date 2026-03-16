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

from tck.requirements.base import tck_id


if TYPE_CHECKING:
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

    Uses the ``tck-task-helper`` prefix which maps to a SUT scenario that
    immediately completes the task.

    Calls ``pytest.skip`` if the task cannot be created.
    """
    message = {
        "role": "ROLE_USER",
        "parts": [{"text": "TCK prerequisite task creation"}],
        "messageId": tck_id("task-helper"),
    }
    return _create_task(client, message)


def create_working_task(client: BaseTransportClient) -> TaskInfo:
    """Create a task that stays in a non-terminal (input_required) state.

    Uses the ``tck-input-required`` prefix which maps to a SUT scenario that
    sets the task status to ``input_required`` instead of completing it.

    Calls ``pytest.skip`` if the task cannot be created.
    """
    message = {
        "role": "ROLE_USER",
        "parts": [{"text": "TCK working task creation"}],
        "messageId": tck_id("input-required"),
    }
    return _create_task(client, message)


def _create_task(client: BaseTransportClient, message: dict[str, Any]) -> TaskInfo:
    """Send a message and return the resulting task identifiers.

    Calls ``pytest.skip`` if the task cannot be created.
    """
    response = client.send_message(message=message)
    if not response.success:
        pytest.skip(f"send_message failed: {response.error}")

    task_id = response.task_id
    if not task_id:
        pytest.skip("Could not extract task ID from send_message response")

    return TaskInfo(
        task_id=task_id,
        context_id=response.context_id,
        transport=response.transport,
    )
