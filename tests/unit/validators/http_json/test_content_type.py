"""Exact matching of the recommended HTTP+JSON media type."""

from __future__ import annotations

import pytest

from tck.validators.http_json.content_type import uses_a2a_media_type


@pytest.mark.parametrize("name", ["content-type", "Content-Type", "CONTENT-TYPE"])
@pytest.mark.parametrize("value", ["application/a2a+json", "Application/A2A+JSON; charset=utf-8", " application/a2a+json "])
def test_recommended_type_allows_case_and_parameters(name: str, value: str) -> None:
    """Allow legal MIME spelling and parameters."""
    assert uses_a2a_media_type({name: value})


@pytest.mark.parametrize("value", ["", "application/json", "application/a2a+json-invalid", "text/application/a2a+json"])
def test_other_types_do_not_satisfy_recommendation(value: str) -> None:
    """Reject other media types and misleading substring matches."""
    assert not uses_a2a_media_type({"Content-Type": value})


def test_absent_header_does_not_satisfy_recommendation() -> None:
    """Require the response to declare its media type."""
    assert not uses_a2a_media_type({})
