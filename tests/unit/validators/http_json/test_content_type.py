"""Exact matching of the recommended HTTP+JSON media type."""

from __future__ import annotations

import pytest

from tck.validators.http_json.content_type import uses_json_media_type, uses_recommended_media_type


@pytest.mark.parametrize("name", ["content-type", "Content-Type", "CONTENT-TYPE"])
@pytest.mark.parametrize("value", ["application/a2a+json", "Application/A2A+JSON; charset=utf-8", " application/a2a+json ", "application/json", "Application/JSON; charset=utf-8"])
def test_recommended_type_allows_case_and_parameters(name: str, value: str) -> None:
    """Allow legal MIME spelling and parameters."""
    assert uses_json_media_type({name: value})


@pytest.mark.parametrize("value", ["", "application/json-invalid", "application/a2a+json-invalid", "text/application/a2a+json"])
def test_other_types_do_not_satisfy_recommendation(value: str) -> None:
    """Reject other media types and misleading substring matches."""
    assert not uses_json_media_type({"Content-Type": value})


def test_absent_header_does_not_satisfy_recommendation() -> None:
    """Require the response to declare its media type."""
    assert not uses_json_media_type({})


@pytest.mark.parametrize(("version", "value", "expected"), [
    ("1.0.0", "Application/JSON; charset=utf-8", True),
    ("1.0.0", "application/a2a+json", False),
    ("1.0.1", "application/json", False),
    ("1.0.1", "Application/A2A+JSON; charset=utf-8", True),
    ("1.0.1", "application/a2a+json-invalid", False),
])
def test_versioned_recommendation(version: str, value: str, expected: bool) -> None:
    """The recommendation is distinct from generic JSON parsing support."""
    assert uses_recommended_media_type({"Content-Type": value}, version) is expected


def test_unknown_version_rejected() -> None:
    """Do not silently choose a recommendation for an unknown release."""
    with pytest.raises(ValueError, match="Unsupported media-type specification version"):
        uses_recommended_media_type({}, "1.0.2")
