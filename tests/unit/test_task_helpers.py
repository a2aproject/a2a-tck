"""Unit tests for shared compatibility task helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from tck.requirements.base import tck_id
from tests.compatibility import _task_helpers


def test_multiturn_task_with_history_uses_unique_message_ids(monkeypatch: Any) -> None:
    """Every send, across repeated calls, needs a distinct ID that keeps its fixture prefix."""
    monkeypatch.setattr(_task_helpers, "validate_task_state", lambda *_args: [])

    class RecordingClient:
        def __init__(self) -> None:
            self.messages: list[dict[str, Any]] = []

        def send_message(self, *, message: dict[str, Any]) -> SimpleNamespace:
            self.messages.append(message)
            return SimpleNamespace(
                success=True,
                error=None,
                task_id="task-1",
                context_id="context-1",
                transport="http_json",
            )

    client = RecordingClient()
    _task_helpers.create_multiturn_task_with_history(client)
    _task_helpers.create_multiturn_task_with_history(client)

    message_ids = [message["messageId"] for message in client.messages]
    assert len(message_ids) == len(set(message_ids))
    sends_per_call = len(message_ids) // 2
    input_required_ids = message_ids[: sends_per_call - 1]
    assert all(message_id.startswith(tck_id("input-required")) for message_id in input_required_ids)
    assert message_ids[sends_per_call - 1].startswith(tck_id("complete-task"))
