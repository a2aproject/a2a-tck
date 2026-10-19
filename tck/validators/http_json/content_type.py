"""HTTP+JSON media type recommendation (spec Section 11.1)."""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping

from tck.requirements.base import HTTP_JSON_CONTENT_TYPE


def uses_a2a_media_type(headers: Mapping[str, str]) -> bool:
    """Check the exact media type, allowing parameters and case-insensitive names."""
    for name, value in headers.items():
        if name.lower() == "content-type":
            return value.partition(";")[0].strip().lower() == HTTP_JSON_CONTENT_TYPE
    return False
