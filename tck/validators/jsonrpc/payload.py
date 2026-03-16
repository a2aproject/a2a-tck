"""JSON-RPC payload validators for A2A protocol responses."""

from __future__ import annotations

from typing import Any


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
