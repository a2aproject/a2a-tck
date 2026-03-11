"""HTTP+JSON payload validators for A2A protocol responses."""

from __future__ import annotations

from typing import Any


def validate_field_is_present(
    response: Any, field: str,
) -> list[str]:
    """Validate that a field is present and non-empty in the HTTP+JSON response body.

    Args:
        response: The transport response object with a ``raw_response`` dict.
        field: The field name to check (e.g. "contextId").

    Returns:
        A list of error strings (empty if the field is present).
    """
    data = response.raw_response
    if not isinstance(data, dict):
        return [f"Response is not a JSON object, cannot check for '{field}'"]
    if not data.get(field):
        return [f"Response must include '{field}'"]
    return []
