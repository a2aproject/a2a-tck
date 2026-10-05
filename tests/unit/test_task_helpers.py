"""Unit tests for shared compatibility task helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from tests.compatibility import _task_helpers


def test_multiturn_task_with_history_uses_unique_message_ids(monkeypatch: Any) -> None:
    """History follow-ups need distinct IDs while matching the input-required fixture."""
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

    message_ids = [message["messageId"] for message in client.messages]
    assert len(message_ids) == len(set(message_ids))
    assert client.messages[1]["messageId"].startswith(message_ids[0])
    assert client.messages[2]["messageId"].startswith(message_ids[0])
