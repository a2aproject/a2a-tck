"""HTTP+JSON payload validators for A2A protocol responses."""

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
    if not isinstance(data, dict):
        return [f"Response is not a JSON object, cannot check state '{expected.json_value}'"]
    task = data.get("task")
    if not isinstance(task, dict):
        return [f"Response does not contain a task, cannot check state '{expected.json_value}'"]
    actual = task.get("status", {}).get("state", "")
    if actual != expected.json_value:
        return [f"Expected task state '{expected.json_value}' but got '{actual}'"]
    return []


def validate_message_response_contains_field(
    response: Any, field: str,
) -> list[str]:
    """Validate that a field is present in the SendMessageResponse body.

    The HTTP+JSON response for SendMessage is a ``SendMessageResponse``
    envelope containing either a ``task`` or ``message`` inner object.  The
    field is looked up in the inner object first, then at the top level.

    Args:
        response: The transport response object with a ``raw_response`` dict.
        field: The field name to check (e.g. "contextId").

    Returns:
        A list of error strings (empty if the field is present).
    """
    data = response.raw_response
    if not isinstance(data, dict):
        return [f"Response is not a JSON object, cannot check for '{field}'"]
    inner = data.get("task") or data.get("message") or data
    if inner.get(field) is None:
        return [f"Response must include '{field}'"]
    return []
