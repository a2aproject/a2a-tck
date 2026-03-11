"""gRPC payload validators for A2A protocol responses."""

from __future__ import annotations

from typing import Any


def validate_field_is_present(
    response: Any, field: str,
) -> list[str]:
    """Validate that a field is present and non-empty in the gRPC response.

    Args:
        response: The transport response object with a ``raw_response`` protobuf message.
        field: The field name to check (e.g. "context_id").

    Returns:
        A list of error strings (empty if the field is present).
    """
    value = getattr(response.raw_response, field, None)
    if not value:
        return [f"Response must include '{field}'"]
    return []
