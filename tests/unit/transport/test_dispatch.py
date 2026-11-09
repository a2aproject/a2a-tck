"""Unit tests for requirement dispatch."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from tck.requirements.base import OperationType, tck_id
from tck.requirements.registry import ALL_REQUIREMENTS
from tck.transport.dispatch import execute_operation


class _RecordingClient:
    """Records the messages that requirements send."""

    transport = "jsonrpc"

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    def send_message(self, message: dict[str, Any], **_kwargs: Any) -> SimpleNamespace:
        self.messages.append(message)
        return SimpleNamespace(success=True)


def test_samples_sharing_a_message_id_send_distinct_ids() -> None:
    """Agents may deduplicate by messageId, so every send needs its own ID (#267)."""
    complete_task = tck_id("complete-task")
    requirements = [
        requirement
        for requirement in ALL_REQUIREMENTS
        if requirement.operation is OperationType.SEND_MESSAGE
        and requirement.sample_input.get("message", {}).get("messageId") == complete_task
    ]
    assert len(requirements) > 1

    client = _RecordingClient()
    for requirement in requirements:
        execute_operation(client, requirement)
    execute_operation(client, requirements[0])

    message_ids = [message["messageId"] for message in client.messages]
    assert len(message_ids) == len(set(message_ids))
    assert all(message_id.startswith(f"{complete_task}-jsonrpc-") for message_id in message_ids)
