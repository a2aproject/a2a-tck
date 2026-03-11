"""JSON-RPC payload validators for A2A protocol responses."""

from __future__ import annotations

from typing import Any


def validate_field_is_present(
    response: Any, field: str,
) -> list[str]:
    """Validate that a field is present and non-empty in the JSON-RPC result.

    Args:
        response: The transport response object with a ``raw_response`` dict.
        field: The field name to check in the ``result`` object (e.g. "contextId").

    Returns:
        A list of error strings (empty if the field is present).
    """
    data = response.raw_response
    result = data.get("result", {})
    if not result.get(field):
        return [f"Response result must include '{field}'"]
    return []
