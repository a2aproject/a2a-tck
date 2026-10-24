"""Tests for HTTP+JSON response media-type validation."""

from __future__ import annotations

import pytest

from tck.requirements.base import RequirementLevel
from tck.requirements.registry import get_requirement_by_id
from tck.validators.http_json.media_type import is_a2a_json_media_type


@pytest.mark.parametrize(
    "content_type",
    [
        "application/a2a+json",
        "application/a2a+json; charset=utf-8",
        "Application/A2A+JSON",
    ],
)
def test_is_a2a_json_media_type_accepts_a2a_json(content_type: str) -> None:
    """The preferred A2A v1.0 media type is matched case-insensitively."""
    assert is_a2a_json_media_type(content_type)


@pytest.mark.parametrize(
    "content_type",
    ["", "application/json", "text/plain", "application/xml", "application/problem+json"],
)
def test_is_a2a_json_media_type_rejects_other_types(content_type: str) -> None:
    """Other JSON types do not satisfy the A2A-specific preference."""
    assert not is_a2a_json_media_type(content_type)


def test_http_json_content_type_requirement_is_should() -> None:
    """Section 11.1 expresses the A2A media type as a SHOULD, not a MUST."""
    requirement = get_requirement_by_id("HTTP_JSON-SVC-001")
    assert requirement.level is RequirementLevel.SHOULD
    assert "application/a2a+json" in requirement.expected_behavior
