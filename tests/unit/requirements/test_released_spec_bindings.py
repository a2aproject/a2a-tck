"""Verify the binding contract against the checked-in, released specification."""

from __future__ import annotations

import re

from pathlib import Path

import pytest

from tck.requirements.base import ERROR_BINDINGS, RequirementLevel
from tck.requirements.registry import ALL_REQUIREMENTS, get_requirement_by_id
from tck.validators.http_json.error_validator import validate_http_json_error


_SPEC = Path(__file__).resolve().parents[3] / "specification" / "specification.md"
_ERROR_ROW = re.compile(
    r"^\| `(?P<name>\w+Error)`\s*\| `(?P<jsonrpc>-\d+)`\s*"
    r"\| `(?P<grpc>\w+)`\s*\| `(?P<http>\d+) [^`]+`\s*\|$",
    re.MULTILINE,
)
_A2A_ERROR_COUNT = 9
_ROWS = [match.groupdict() for match in _ERROR_ROW.finditer(_SPEC.read_text())]


def test_released_spec_error_table_is_complete() -> None:
    """A changed table format cannot silently disable the contract checks."""
    assert len(_ROWS) == _A2A_ERROR_COUNT
    assert {row["name"] for row in _ROWS} == {
        name for name, binding in ERROR_BINDINGS.items() if binding.reason is not None
    }


@pytest.mark.parametrize("row", _ROWS, ids=lambda row: row["name"])
def test_all_error_bindings_match_released_spec(row: dict[str, str]) -> None:
    """Derive all three transport expectations independently from the released table."""
    binding = ERROR_BINDINGS[row["name"]]
    assert binding.jsonrpc_code == int(row["jsonrpc"])
    assert binding.grpc_status == row["grpc"]
    assert binding.http_status == int(row["http"])
    response = {"status_code": int(row["http"]), "body": {"error": {
        "code": int(row["http"]), "message": "conformant error",
        "details": [{"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": binding.reason, "domain": "a2a-protocol.org"}],
    }}}
    assert validate_http_json_error(response, row["name"]).valid


@pytest.mark.parametrize(
    ("requirement_id", "level"),
    [("HTTP_JSON-SVC-001", RequirementLevel.SHOULD), ("JSONRPC-ERR-003", RequirementLevel.SHOULD)],
)
def test_released_recommendations_are_not_musts(requirement_id: str, level: RequirementLevel) -> None:
    """Preserve the normative level when selecting and reporting tests."""
    assert get_requirement_by_id(requirement_id).level is level


def test_rest_schema_validation_remains_mandatory() -> None:
    """A media type recommendation must not weaken structural validation."""
    assert get_requirement_by_id("HTTP_JSON-FMT-001").level is RequirementLevel.MUST


def test_requirement_anchors_match_the_vendored_spec() -> None:
    """Keep every requirement's citation attached to an actual specification heading."""
    headings = re.findall(r"^#{1,6}\s+(.+)", _SPEC.read_text(), re.MULTILINE)
    anchors = {re.sub(r"[^\w\- ]", "", heading).strip().lower().replace(" ", "-"): heading for heading in headings}
    for requirement in ALL_REQUIREMENTS:
        anchor = requirement.spec_url.split("#")[-1]
        assert anchor in anchors, requirement.id
        section = re.match(r"(\d+(?:\.\d+)*)\.?\s", anchors[anchor])
        assert section is not None and section.group(1) == requirement.section, requirement.id


@pytest.mark.parametrize("transport,requirement_id,column", [
    ("grpc", "GRPC-ERR-002", "grpc"), ("jsonrpc", "JSONRPC-SSE-002", "jsonrpc"),
    ("http_json", "HTTP_JSON-STATUS-001", "http"),
])
def test_reported_error_mapping_prose_tracks_the_released_table(transport: str, requirement_id: str, column: str) -> None:
    """The human report and its executable validators must describe the same mapping."""
    description = get_requirement_by_id(requirement_id).description
    for row in _ROWS:
        assert f"{row['name']}={row[column]}" in description, (transport, row["name"])


def test_mapping_description_rejects_an_unknown_transport() -> None:
    """A bad report producer cannot silently emit an empty mapping table."""
    from tck.requirements.base import describe_error_mappings

    with pytest.raises(ValueError, match="No smtp mapping"):
        describe_error_mappings("smtp")
