"""HTTP+JSON media type recommendation (spec Section 11.1)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tck.requirements.base import HTTP_JSON_CONTENT_TYPE


if TYPE_CHECKING:
    from collections.abc import Mapping


def uses_json_media_type(headers: Mapping[str, str]) -> bool:
    """Accept the A2A and generic JSON media types, including parameters."""
    for name, value in headers.items():
        if name.lower() == "content-type":
            return value.partition(";")[0].strip().lower() in {HTTP_JSON_CONTENT_TYPE, "application/json"}
    return False
