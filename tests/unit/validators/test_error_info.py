"""Required ProtoJSON Any structure is independent of optional well-known types."""

from __future__ import annotations

import pytest

from tck.validators.error_info import uses_well_known_error_details, validate_error_details, validate_error_info


@pytest.mark.parametrize("details", [[], [{"@type": "example.org/Custom", "value": None}], [{"@type": "type.googleapis.com/google.rpc.BadRequest"}]])
def test_error_details_allow_empty_and_custom_typed_arrays(details: list) -> None:
    """Allow valid Any arrays without mandating a particular schema."""
    assert validate_error_details(details) == []


@pytest.mark.parametrize("details", [None, {}, "error", [None], [7], [{}], [{"@type": None}], [{"@type": 1}], [{"@type": ""}]])
def test_error_details_reject_malformed_any_structure(details: object) -> None:
    """Reject each malformed array and Any-object shape."""
    assert validate_error_details(details)


def test_http_error_info_cannot_hide_invalid_sibling_details() -> None:
    """Check every detail object even when a valid ErrorInfo exists."""
    details = [{"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": "TASK_NOT_FOUND", "domain": "a2a-protocol.org"}, {}]
    result = validate_error_info(details)
    assert not result.valid
    assert "detail 1" in result.message


@pytest.mark.parametrize("name", ["ErrorInfo", "BadRequest", "ResourceInfo", "RetryInfo"])
def test_well_known_recommendation_is_not_limited_to_error_info(name: str) -> None:
    """Recognize other standard google.rpc detail types."""
    assert uses_well_known_error_details([{"@type": f"type.googleapis.com/google.rpc.{name}"}])


@pytest.mark.parametrize("details", [[], None, {}, [{}], [{"@type": "example.org/Custom"}], [{"@type": "type.googleapis.com/google.rpc.Unknown"}]])
def test_custom_or_absent_details_do_not_satisfy_recommendation(details: object) -> None:
    """Keep valid custom details distinct from the well-known recommendation."""
    assert not uses_well_known_error_details(details)
