"""Media-type helpers for the HTTP+JSON binding."""

from __future__ import annotations


A2A_JSON_MEDIA_TYPE = "application/a2a+json"


def is_a2a_json_media_type(content_type: str) -> bool:
    """Return whether a Content-Type value uses the A2A JSON media type."""
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type == A2A_JSON_MEDIA_TYPE
