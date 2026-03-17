"""gRPC payload validators for A2A protocol responses."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from specification.generated import a2a_pb2


if TYPE_CHECKING:
    from tck.requirements.base import TaskStateBinding


def validate_task_state(response: Any, expected: TaskStateBinding) -> list[str]:
    """Validate that the task in a SendMessageResponse has the expected state.

    Args:
        response: The transport response object with a ``raw_response`` protobuf.
        expected: The expected ``TaskStateBinding``.

    Returns:
        A list of error strings (empty if the state matches).
    """
    msg = response.raw_response
    expected_name = a2a_pb2.TaskState.Name(expected.grpc_value)
    # SendMessageResponse has a "payload" oneof.
    task = getattr(msg, "task", None)
    if task is None:
        return [f"Response does not contain a task, cannot check state '{expected_name}'"]
    actual = task.status.state
    if actual != expected.grpc_value:
        try:
            actual_name = a2a_pb2.TaskState.Name(actual)
        except ValueError:
            actual_name = str(actual)
        return [f"Expected task state '{expected_name}' but got '{actual_name}'"]
    return []


def validate_message_response_contains_field(
    response: Any, field: str,
) -> list[str]:
    """Validate that a field is present in the SendMessageResponse.

    The gRPC response for SendMessage is a ``SendMessageResponse`` protobuf
    with a ``task`` or ``message`` oneof field.  The field is looked up in
    the inner object first, then on the top-level response.

    Args:
        response: The transport response object with a ``raw_response`` protobuf message.
        field: The field name to check (e.g. "context_id").

    Returns:
        A list of error strings (empty if the field is present).
    """
    msg = response.raw_response
    inner = getattr(msg, "task", None) or getattr(msg, "message", None) or msg
    value = getattr(inner, field, None)
    if value is None:
        return [f"Response must include '{field}'"]
    return []
