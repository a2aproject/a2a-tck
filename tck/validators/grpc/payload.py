"""gRPC payload validators and extractors for A2A protocol responses."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from specification.generated import a2a_pb2


if TYPE_CHECKING:
    from tck.requirements.base import TaskStateBinding


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def extract_artifacts(response: Any) -> list[Any]:
    """Extract artifacts from a gRPC SendMessageResponse."""
    msg = response.raw_response
    if hasattr(msg, "WhichOneof"):
        payload = msg.WhichOneof("payload")
        if payload == "task":
            return list(msg.task.artifacts)
    return []


def extract_message(response: Any) -> Any | None:
    """Extract a Message payload from a gRPC SendMessageResponse."""
    msg = response.raw_response
    if hasattr(msg, "WhichOneof"):
        payload = msg.WhichOneof("payload")
        if payload == "message":
            return msg.message
    return None


def extract_history(response: Any) -> list[Any]:
    """Extract history messages from a gRPC response."""
    msg = response.raw_response
    # Task proto returned directly (GetTask, CancelTask)
    if hasattr(msg, "history") and not hasattr(msg, "WhichOneof"):
        return list(msg.history)
    # SendMessageResponse has a "payload" oneof wrapping the Task
    try:
        if hasattr(msg, "WhichOneof"):
            payload = msg.WhichOneof("payload")
            if payload == "task":
                return list(msg.task.history)
    except ValueError:
        pass
    # Fallback for direct Task proto with WhichOneof from other fields
    if hasattr(msg, "history"):
        return list(msg.history)
    return []


def get_part_type(part: Any) -> str | None:
    """Determine which oneof content variant is set on a Part."""
    if hasattr(part, "WhichOneof"):
        return part.WhichOneof("content")
    return None


def get_part_text(part: Any) -> str | None:
    """Extract text content from a Part."""
    if not hasattr(part, "WhichOneof"):
        return None
    return part.text if part.WhichOneof("content") == "text" else None


def get_part_filename(part: Any) -> str | None:
    """Extract filename from a Part."""
    return part.filename or None


def get_part_media_type(part: Any) -> str | None:
    """Extract media type from a Part."""
    return part.media_type or None


def get_part_data(part: Any) -> Any | None:
    """Extract data content from a Part."""
    if not hasattr(part, "WhichOneof"):
        return None
    if part.WhichOneof("content") == "data":
        from google.protobuf.json_format import MessageToDict

        return MessageToDict(part.data)
    return None


def get_artifact_id(artifact: Any) -> str | None:
    """Extract artifactId from an Artifact."""
    return artifact.artifact_id or None


def get_artifact_parts(artifact: Any) -> list[Any]:
    """Extract parts from an Artifact."""
    return list(artifact.parts)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


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
