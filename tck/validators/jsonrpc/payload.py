"""JSON-RPC payload validators for A2A protocol responses."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from tck.requirements.base import TaskStateBinding


def validate_task_state(response: Any, expected: TaskStateBinding) -> list[str]:
    """Validate that the task in a SendMessageResponse has the expected state.

    Args:
        response: The transport response object with a ``raw_response`` dict.
        expected: The expected ``TaskStateBinding``.

    Returns:
        A list of error strings (empty if the state matches).
    """
    data = response.raw_response
    result = data.get("result", {})
    task = result.get("task") if isinstance(result, dict) else None
    if not isinstance(task, dict):
        return [f"Response result does not contain a task, cannot check state '{expected.json_value}'"]
    actual = task.get("status", {}).get("state", "")
    if actual != expected.json_value:
        return [f"Expected task state '{expected.json_value}' but got '{actual}'"]
    return []


def validate_message_response_contains_field(
    response: Any, field: str,
) -> list[str]:
    """Validate that a field is present in the SendMessageResponse result.

    The JSON-RPC result for SendMessage is a ``SendMessageResponse`` envelope
    containing either a ``task`` or ``message`` inner object.  The field is
    looked up in the inner object first, then at the top level of ``result``.

    Args:
        response: The transport response object with a ``raw_response`` dict.
        field: The field name to check (e.g. "contextId").

    Returns:
        A list of error strings (empty if the field is present).
    """
    data = response.raw_response
    result = data.get("result", {})
    inner = result.get("task") or result.get("message") or result
    if inner.get(field) is None:
        return [f"Response result must include '{field}'"]
    return []
