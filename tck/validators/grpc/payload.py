"""gRPC payload validators for A2A protocol responses."""

from __future__ import annotations

from typing import Any


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
