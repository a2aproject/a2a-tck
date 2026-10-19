"""Manual obligations stay pending without weakening missing automated checks."""

from __future__ import annotations

import json

from itertools import permutations

import pytest

from tck.reporting.aggregator import CompatibilityAggregator
from tck.reporting.collector import CompatibilityCollector
from tck.reporting.console_formatter import ConsoleFormatter
from tck.reporting.html_formatter import HTMLFormatter
from tck.reporting.json_formatter import JSONFormatter
from tck.requirements.base import RequirementLevel
from tck.requirements.registry import ALL_REQUIREMENTS
from tck.requirements.tags import NOT_AUTOMATABLE


_FULL = 100.0

def automated_results(*, omit: str = "") -> CompatibilityCollector:
    """Exercise the actual registry, without replacing its manual tags."""
    collector = CompatibilityCollector()
    for requirement in ALL_REQUIREMENTS:
        if NOT_AUTOMATABLE not in requirement.tags and requirement.id != omit:
            collector.record(requirement_id=requirement.id, transport="control", level=requirement.level.value, passed=True)
    return collector


def test_manual_requirements_do_not_become_phantom_failures_or_passes() -> None:
    """Every unexercised manual obligation is explicit and outside automated scores."""
    report = CompatibilityAggregator(automated_results()).aggregate()
    manual_ids = {requirement.id for requirement in ALL_REQUIREMENTS if NOT_AUTOMATABLE in requirement.tags}
    assert {"CARD-CLIENT-001", "BIND-CUSTOM-002"} <= manual_ids
    assert {req_id for req_id, requirement in report.per_requirement.items() if requirement.status == "MANUAL"} == manual_ids
    assert report.must_compatibility == _FULL
    assert report.overall_compatibility == _FULL
    assert set(report.pending_manual) == manual_ids
    assert set(report.to_dict()["manual_verification_required"]) == manual_ids

    console = ConsoleFormatter(color=False).format(report)
    html = HTMLFormatter().format(report)
    data = json.loads(JSONFormatter().format(report))
    assert "automated checks" in console
    assert "Manual" in console
    must_row = next(line for line in console.splitlines() if line.startswith("│ MUST"))
    columns = [value.strip() for value in must_row.split("│")[1:-1]]
    assert int(columns[2]) == 0
    assert int(columns[4]) == sum(requirement.level == "MUST" for requirement in report.pending_manual.values())
    assert "PENDING MANUAL VERIFICATION" in console
    assert "Automated checks" in html
    assert '<td class="manual">MANUAL</td>' in html
    assert data["summary"]["score_scope"] == "automated"
    assert set(data["summary"]["manual_verification_required"]) == manual_ids
    for req_id in manual_ids:
        assert req_id in console and req_id in html
        assert data["per_requirement"][req_id]["status"] == "MANUAL"


def test_missing_automatable_requirement_still_lowers_the_score() -> None:
    """Manual exclusions must not revive the unreachable-SUT false green."""
    requirement = next(req for req in ALL_REQUIREMENTS if req.level is RequirementLevel.MUST and NOT_AUTOMATABLE not in req.tags)
    report = CompatibilityAggregator(automated_results(omit=requirement.id)).aggregate()
    assert report.per_requirement[requirement.id].status == "NOT TESTED"
    assert report.must_compatibility < _FULL
    assert report.overall_compatibility < _FULL


@pytest.mark.parametrize("outcomes", list(permutations(["PASS", "FAIL", "SKIPPED"])))
def test_later_results_cannot_hide_a_failure_on_the_same_transport(outcomes: tuple[str, ...]) -> None:
    """Per-transport detail preserves failures regardless of execution order."""
    collector = CompatibilityCollector()
    for outcome in outcomes:
        collector.record(requirement_id="CORE-SEND-001", transport="http_json", level="MUST",
                         passed=outcome == "PASS", skipped=outcome == "SKIPPED", errors=["witness"] if outcome == "FAIL" else [])
    report = CompatibilityAggregator(collector).aggregate()
    result = report.per_requirement["CORE-SEND-001"]
    assert result.status == "FAIL"
    assert result.transports["http_json"] == "FAIL"
    assert result.transport_errors == {"http_json": ["witness"]}
