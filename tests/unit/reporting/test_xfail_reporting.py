"""Tests for xfail-aware result recording and reporting consistency.

Regression coverage for issue #234: tests that record a requirement as failed
and then ``pytest.xfail`` must not surface as non-compliant (``FAIL``) in
``compatibility.json`` while the pytest suite exits 0.
"""

from __future__ import annotations

from tck.reporting.aggregator import CompatibilityAggregator, RequirementResult
from tck.reporting.collector import CompatibilityCollector, TestResult, summarize_status


FULL_COMPAT = 100.0
ZERO_COMPAT = 0.0
THREE = 3


class TestSummarizeStatusXfail:
    """summarize_status distinguishes known failures from hard failures."""

    def test_xfail_result_does_not_fail_the_requirement(self) -> None:
        """A single xfail result summarizes as XFAIL, not FAIL."""
        assert summarize_status([_result(passed=False, xfail=True)]) == "XFAIL"

    def test_hard_failure_still_dominates_xfail(self) -> None:
        """A hard failure dominates an xfail result for the same obligation."""
        results = [_result(passed=False, xfail=True), _result(passed=False)]
        assert summarize_status(results) == "FAIL"

    def test_xfail_dominates_pass(self) -> None:
        """An xfail result is more informative than a pass."""
        results = [_result(passed=True), _result(passed=False, xfail=True)]
        assert summarize_status(results) == "XFAIL"

    def test_xfail_dominates_skip(self) -> None:
        """An xfail result is more informative than a skip."""
        results = [_result(passed=False, skipped=True), _result(passed=False, xfail=True)]
        assert summarize_status(results) == "XFAIL"

    def test_plain_results_are_unaffected(self) -> None:
        """Results without the xfail flag keep the original semantics."""
        assert summarize_status([_result(passed=True)]) == "PASS"
        assert summarize_status([_result(passed=False, skipped=True)]) == "SKIPPED"


class TestCollectorTransportCounts:
    """get_per_transport counts xfailed results separately from failed."""

    def test_xfail_is_not_counted_as_failed(self) -> None:
        """An xfail-marked result is reported as xfailed, not failed."""
        collector = CompatibilityCollector()
        collector.record(requirement_id="CORE-A", transport="jsonrpc", passed=True)
        collector.record(
            requirement_id="CORE-B",
            transport="jsonrpc",
            passed=False,
            errors=["known checker limitation"],
            xfail=True,
        )
        collector.record(requirement_id="CORE-C", transport="jsonrpc", passed=False, errors=["boom"])

        counts = collector.get_per_transport()["jsonrpc"]
        assert counts["passed"] == 1
        assert counts["xfailed"] == 1
        assert counts["failed"] == 1
        assert counts["total"] == THREE

    def test_xfail_flag_defaults_to_false(self) -> None:
        """Records without the xfail flag keep counting as failed."""
        collector = CompatibilityCollector()
        collector.record(requirement_id="CORE-A", transport="grpc", passed=False, errors=["boom"])

        counts = collector.get_per_transport()["grpc"]
        assert counts["xfailed"] == 0
        assert counts["failed"] == 1

    def test_per_requirement_status_is_xfail(self) -> None:
        """get_per_requirement surfaces the XFAIL status."""
        collector = CompatibilityCollector()
        collector.record(
            requirement_id="DM-SERIAL-003",
            transport="jsonrpc",
            passed=False,
            errors=["known checker limitation"],
            xfail=True,
        )

        per_requirement = collector.get_per_requirement()
        assert per_requirement["DM-SERIAL-003"]["status"] == "XFAIL"


class TestCompatibilityExcludesXfail:
    """The compatibility denominator must not count XFAIL as non-compliant."""

    @staticmethod
    def _req(status: str) -> RequirementResult:
        """Build a minimal RequirementResult with the given status."""
        return RequirementResult(
            level="MUST",
            status=status,
            transports={},
            errors=[],
            description="",
            spec_url="",
            transport_errors={},
            test_ids=[],
        )

    def test_xfail_requirement_is_excluded_from_denominator(self) -> None:
        """An all-XFAIL obligation leaves the compatibility score untouched."""
        per_requirement = {"DM-SERIAL-003": self._req("XFAIL")}
        # Static helper, exercised directly to keep untested requirements out of the fixture.
        assert CompatibilityAggregator._compute_compatibility(per_requirement, level=None) == FULL_COMPAT  # noqa: SLF001

    def test_fail_requirement_still_scores_zero(self) -> None:
        """A FAIL obligation keeps dragging the compatibility score to zero."""
        per_requirement = {"CORE-A": self._req("FAIL")}
        assert CompatibilityAggregator._compute_compatibility(per_requirement, level=None) == ZERO_COMPAT  # noqa: SLF001


def _result(*, passed: bool, skipped: bool = False, xfail: bool = False) -> TestResult:
    """Build a minimal TestResult with the given outcome flags."""
    return TestResult(
        requirement_id="CORE-A",
        transport="jsonrpc",
        passed=passed,
        skipped=skipped,
        xfail=xfail,
    )
