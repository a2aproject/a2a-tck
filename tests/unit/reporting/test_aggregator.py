"""Tests for the ComplianceAggregator."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tck.reporting.aggregator import ComplianceAggregator
from tck.reporting.collector import ComplianceCollector


FULL = 100.0
HALF = 50.0
ZERO = 0.0


@pytest.fixture
def collector() -> ComplianceCollector:
    """Return a fresh ComplianceCollector."""
    return ComplianceCollector()


class TestEmptyCollector:
    """Aggregating an empty collector."""

    def test_empty_gives_100_percent(self, collector: ComplianceCollector) -> None:
        """Empty collector yields 100% compliance everywhere."""
        with patch("tck.requirements.registry.ALL_REQUIREMENTS", []):
            report = ComplianceAggregator(collector).aggregate()
        assert report.overall_compliance == FULL
        assert report.must_compliance == FULL
        assert report.should_compliance == FULL
        assert report.may_compliance == FULL
        assert report.per_requirement == {}
        assert report.per_transport == {}


class TestAllPassing:
    """All MUST requirements passing."""

    def test_all_must_passing(self, collector: ComplianceCollector) -> None:
        """All MUST requirements pass yields 100% compliance."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        collector.record(requirement_id="R2", transport="http", passed=True, level="MUST")

        report = ComplianceAggregator(collector).aggregate()
        assert report.must_compliance == FULL
        assert report.overall_compliance == FULL
        assert report.per_requirement["R1"].status == "PASS"
        assert report.per_requirement["R2"].status == "PASS"


class TestMixedPassFail:
    """Mixed pass/fail across levels."""

    def test_mixed_compliance(self, collector: ComplianceCollector) -> None:
        """One MUST pass and one MUST fail yields 50% MUST compliance."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        collector.record(requirement_id="R2", transport="http", passed=False, level="MUST")
        collector.record(requirement_id="R3", transport="http", passed=True, level="SHOULD")

        report = ComplianceAggregator(collector).aggregate()
        assert report.must_compliance == HALF
        assert report.should_compliance == FULL

    def test_overall_includes_all_levels(self, collector: ComplianceCollector) -> None:
        """Overall compliance considers requirements across all levels."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        collector.record(requirement_id="R2", transport="http", passed=False, level="SHOULD")

        report = ComplianceAggregator(collector).aggregate()
        assert report.overall_compliance == HALF


class TestRequirementAcrossTransports:
    """A requirement failing on one transport is FAIL overall."""

    def test_fail_on_one_transport(self, collector: ComplianceCollector) -> None:
        """Requirement failing on grpc but passing on http is FAIL overall."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        collector.record(requirement_id="R1", transport="grpc", passed=False, level="MUST")

        report = ComplianceAggregator(collector).aggregate()
        req = report.per_requirement["R1"]
        assert req.status == "FAIL"
        assert req.transports == {"http": "PASS", "grpc": "FAIL"}

    def test_pass_on_all_transports(self, collector: ComplianceCollector) -> None:
        """Requirement passing on all transports is PASS overall."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        collector.record(requirement_id="R1", transport="grpc", passed=True, level="MUST")

        report = ComplianceAggregator(collector).aggregate()
        req = report.per_requirement["R1"]
        assert req.status == "PASS"
        assert req.transports == {"http": "PASS", "grpc": "PASS"}


class TestPerTransport:
    """Per-transport counts are correct."""

    def test_transport_counts(self, collector: ComplianceCollector) -> None:
        """Per-transport totals, passed, and failed are counted correctly."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        collector.record(requirement_id="R2", transport="http", passed=False, level="MUST")
        collector.record(requirement_id="R3", transport="grpc", passed=True, level="MUST")

        report = ComplianceAggregator(collector).aggregate()
        http = report.per_transport["http"]
        grpc = report.per_transport["grpc"]
        expected_http_total = 2
        assert http.total == expected_http_total
        assert http.passed == 1
        assert http.failed == 1
        assert grpc.total == 1
        assert grpc.passed == 1
        assert grpc.failed == 0


class TestLevelSpecific:
    """Level-specific compliance computed independently."""

    def test_independent_levels(self, collector: ComplianceCollector) -> None:
        """Each level's compliance is computed independently."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        collector.record(requirement_id="R2", transport="http", passed=False, level="SHOULD")
        collector.record(requirement_id="R3", transport="http", passed=True, level="MAY")
        collector.record(requirement_id="R4", transport="http", passed=True, level="MAY")

        report = ComplianceAggregator(collector).aggregate()
        assert report.must_compliance == FULL
        assert report.should_compliance == ZERO
        assert report.may_compliance == FULL


class TestToDict:
    """to_dict() returns a JSON-serialisable dict."""

    def test_to_dict_serializable(self, collector: ComplianceCollector) -> None:
        """to_dict() returns a plain dict with correct structure."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")

        report = ComplianceAggregator(collector).aggregate()
        d = report.to_dict()

        assert isinstance(d, dict)
        assert isinstance(d["per_requirement"], dict)
        assert isinstance(d["per_requirement"]["R1"], dict)
        assert d["per_requirement"]["R1"]["status"] == "PASS"
        assert isinstance(d["overall_compliance"], float)

    def test_to_dict_has_timestamp(self, collector: ComplianceCollector) -> None:
        """to_dict() includes an ISO 8601 timestamp."""
        report = ComplianceAggregator(collector).aggregate()
        d = report.to_dict()
        assert "timestamp" in d
        assert isinstance(d["timestamp"], str)


class TestSkippedStatus:
    """Skipped tests are tracked separately from pass/fail."""

    def test_skipped_only_requirement(self, collector: ComplianceCollector) -> None:
        """Requirement with only skipped results has status SKIPPED."""
        collector.record(requirement_id="R1", transport="http", passed=False, level="MUST", skipped=True)

        report = ComplianceAggregator(collector).aggregate()
        assert report.per_requirement["R1"].status == "SKIPPED"
        assert report.per_requirement["R1"].transports == {"http": "SKIPPED"}

    def test_mixed_pass_and_skipped(self, collector: ComplianceCollector) -> None:
        """Requirement passing on one transport and skipped on another is PASS."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        collector.record(requirement_id="R1", transport="grpc", passed=False, level="MUST", skipped=True)

        report = ComplianceAggregator(collector).aggregate()
        assert report.per_requirement["R1"].status == "PASS"
        assert report.per_requirement["R1"].transports == {"http": "PASS", "grpc": "SKIPPED"}

    def test_mixed_fail_and_skipped(self, collector: ComplianceCollector) -> None:
        """Requirement failing on one transport and skipped on another is FAIL."""
        collector.record(
            requirement_id="R1", transport="http", passed=False, level="MUST", errors=["err"]
        )
        collector.record(requirement_id="R1", transport="grpc", passed=False, level="MUST", skipped=True)

        report = ComplianceAggregator(collector).aggregate()
        assert report.per_requirement["R1"].status == "FAIL"

    def test_skipped_excluded_from_compliance(self, collector: ComplianceCollector) -> None:
        """Skipped requirements are excluded from compliance percentage."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        collector.record(requirement_id="R2", transport="http", passed=False, level="MUST", skipped=True)

        report = ComplianceAggregator(collector).aggregate()
        # R1 passes, R2 skipped → only R1 counts → 100%
        assert report.must_compliance == FULL
        assert report.overall_compliance == FULL

    def test_per_transport_includes_skipped(self, collector: ComplianceCollector) -> None:
        """Per-transport counts include a skipped field."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        collector.record(requirement_id="R2", transport="http", passed=False, level="MUST", skipped=True)

        report = ComplianceAggregator(collector).aggregate()
        http = report.per_transport["http"]
        assert http.passed == 1
        assert http.skipped == 1
        assert http.failed == 0
        expected_total = 2
        assert http.total == expected_total


class TestErrorAggregation:
    """Errors are aggregated from failing results."""

    def test_errors_collected(self, collector: ComplianceCollector) -> None:
        """Errors from all failing transports are aggregated."""
        collector.record(
            requirement_id="R1",
            transport="http",
            passed=False,
            errors=["bad status"],
            level="MUST",
        )
        collector.record(
            requirement_id="R1",
            transport="grpc",
            passed=False,
            errors=["timeout", "connection refused"],
            level="MUST",
        )

        report = ComplianceAggregator(collector).aggregate()
        req = report.per_requirement["R1"]
        assert req.errors == ["bad status", "timeout", "connection refused"]

    def test_passing_has_no_errors(self, collector: ComplianceCollector) -> None:
        """Passing requirement has an empty errors list."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")

        report = ComplianceAggregator(collector).aggregate()
        assert report.per_requirement["R1"].errors == []


class TestUntestedRequirements:
    """Untested requirements from the registry appear with NOT TESTED status."""

    def _make_spec(self, req_id: str, level: str) -> object:
        """Create a minimal RequirementSpec-like object."""
        from tck.requirements.base import RequirementLevel, RequirementSpec

        return RequirementSpec(
            id=req_id,
            title=f"Title for {req_id}",
            description=f"Description for {req_id}",
            level=RequirementLevel(level),
            section="1.0",
        )

    def test_untested_requirements_included(self, collector: ComplianceCollector) -> None:
        """Requirements in registry but not tested appear as NOT TESTED."""
        fake_registry = [
            self._make_spec("R1", "MUST"),
            self._make_spec("R-UNTESTED", "SHOULD"),
        ]
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")

        with patch("tck.requirements.registry.ALL_REQUIREMENTS", fake_registry):
            report = ComplianceAggregator(collector).aggregate()

        assert "R-UNTESTED" in report.per_requirement
        untested = report.per_requirement["R-UNTESTED"]
        assert untested.status == "NOT TESTED"
        assert untested.level == "SHOULD"
        assert untested.transports == {}
        assert untested.description == "Description for R-UNTESTED"

    def test_untested_excluded_from_compliance(self, collector: ComplianceCollector) -> None:
        """NOT TESTED requirements do not affect compliance percentages."""
        fake_registry = [
            self._make_spec("R1", "MUST"),
            self._make_spec("R-UNTESTED", "MUST"),
        ]
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")

        with patch("tck.requirements.registry.ALL_REQUIREMENTS", fake_registry):
            report = ComplianceAggregator(collector).aggregate()

        assert report.must_compliance == FULL
        assert report.overall_compliance == FULL

    def test_tested_requirement_not_overwritten(self, collector: ComplianceCollector) -> None:
        """A requirement that was tested keeps its actual result."""
        fake_registry = [self._make_spec("R1", "MUST")]
        collector.record(requirement_id="R1", transport="http", passed=False, level="MUST")

        with patch("tck.requirements.registry.ALL_REQUIREMENTS", fake_registry):
            report = ComplianceAggregator(collector).aggregate()

        assert report.per_requirement["R1"].status == "FAIL"
