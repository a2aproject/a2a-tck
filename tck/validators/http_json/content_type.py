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


def recommended_media_type(spec_version: str) -> str:
    """Return the HTTP+JSON media type specified by the selected release."""
    if spec_version == "1.0.0":
        return "application/json"
    if spec_version == "1.0.1":
        return HTTP_JSON_CONTENT_TYPE
    raise ValueError(f"Unsupported media-type specification version: {spec_version}")


def uses_recommended_media_type(headers: Mapping[str, str], spec_version: str) -> bool:
    """Match the selected release's media type, allowing case and parameters."""
    expected = recommended_media_type(spec_version)
    for name, value in headers.items():
        if name.lower() == "content-type":
            return value.partition(";")[0].strip().lower() == expected
    return False
