"""Tests for requirement operation dispatch."""

from __future__ import annotations

from typing import Any

from tck.requirements.base import (
    CONTENT_TYPE_NOT_SUPPORTED_ERROR,
    OperationType,
    RequirementLevel,
    RequirementSpec,
)
from tck.transport.dispatch import execute_operation


class _Client:
    transport = "http_json"

    def __init__(self) -> None:
        self.message: dict[str, Any] | None = None

    def send_message(self, message: dict[str, Any]) -> object:
        self.message = message
        return object()


def _requirement() -> RequirementSpec:
    return RequirementSpec(
        id="TEST-SEND-001",
        section="test",
        title="test",
        level=RequirementLevel.MUST,
        description="test requirement",
        operation=OperationType.SEND_MESSAGE,
        sample_input={
            "message": {
                "role": "ROLE_USER",
                "messageId": "original-id",
                "contextId": "original-context",
                "parts": [{"text": "generic fixture"}],
            }
        },
    )


def test_execute_operation_overrides_only_message_parts() -> None:
    """Custom parts preserve scenario identity and all other request fields."""
    client = _Client()
    custom_parts = [{"data": {"invoiceId": "INV-1"}}]

    execute_operation(client, _requirement(), message_parts=custom_parts)

    assert client.message == {
        "role": "ROLE_USER",
        "messageId": "original-id-http_json",
        "contextId": "original-context",
        "parts": custom_parts,
    }


def test_execute_operation_does_not_mutate_custom_parts() -> None:
    """Dispatch deep-copies operator input before passing it to a client."""
    client = _Client()
    custom_parts = [{"data": {"invoiceId": "INV-1"}}]

    execute_operation(client, _requirement(), message_parts=custom_parts)
    assert client.message is not None
    client.message["parts"][0]["data"]["invoiceId"] = "changed"

    assert custom_parts == [{"data": {"invoiceId": "INV-1"}}]


def test_execute_operation_preserves_deliberate_error_parts() -> None:
    """Operator input cannot erase the condition an error scenario exercises."""
    client = _Client()
    requirement = _requirement()
    requirement.expected_error = CONTENT_TYPE_NOT_SUPPORTED_ERROR

    execute_operation(
        client,
        requirement,
        message_parts=[{"data": {"invoiceId": "INV-1"}}],
    )

    assert client.message is not None
    assert client.message["parts"] == [{"text": "generic fixture"}]
