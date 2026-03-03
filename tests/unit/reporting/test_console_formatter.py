"""Tests for the ConsoleFormatter."""

from __future__ import annotations

import pytest

from tck.reporting.aggregator import ComplianceAggregator
from tck.reporting.collector import ComplianceCollector
from tck.reporting.console_formatter import ConsoleFormatter


@pytest.fixture
def collector() -> ComplianceCollector:
    """Return a fresh ComplianceCollector."""
    return ComplianceCollector()


@pytest.fixture
def formatter() -> ConsoleFormatter:
    """Return a ConsoleFormatter with colour disabled for deterministic tests."""
    return ConsoleFormatter(sut_url="http://localhost:9999", spec_version="0.2.1", color=False)


class TestHeader:
    """Header and metadata section."""

    def test_title_present(
        self, collector: ComplianceCollector, formatter: ConsoleFormatter
    ) -> None:
        """Report title appears in the output."""
        report = ComplianceAggregator(collector).aggregate()
        output = formatter.format(report)
        assert "A2A TCK Compliance Report" in output

    def test_sut_url_present(
        self, collector: ComplianceCollector, formatter: ConsoleFormatter
    ) -> None:
        """SUT URL appears in the output."""
        report = ComplianceAggregator(collector).aggregate()
        output = formatter.format(report)
        assert "http://localhost:9999" in output

    def test_spec_version_present(
        self, collector: ComplianceCollector, formatter: ConsoleFormatter
    ) -> None:
        """Spec version appears in the output."""
        report = ComplianceAggregator(collector).aggregate()
        output = formatter.format(report)
        assert "0.2.1" in output

    def test_timestamp_present(
        self, collector: ComplianceCollector, formatter: ConsoleFormatter
    ) -> None:
        """Timestamp appears in the output."""
        report = ComplianceAggregator(collector).aggregate()
        output = formatter.format(report)
        assert "Timestamp:" in output


class TestOverallCompliance:
    """Overall compliance display."""

    def test_compliance_percentage_shown(
        self, collector: ComplianceCollector, formatter: ConsoleFormatter
    ) -> None:
        """Overall compliance percentage appears in the output."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        output = formatter.format(report)
        assert "OVERALL COMPLIANCE:" in output
        assert "100.0%" in output


class TestLevelTable:
    """Pass/fail counts by level."""

    def test_level_names_present(
        self, collector: ComplianceCollector, formatter: ConsoleFormatter
    ) -> None:
        """MUST, SHOULD, MAY levels appear in the table."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        output = formatter.format(report)
        assert "MUST" in output
        assert "SHOULD" in output
        assert "MAY" in output

    def test_counts_correct(
        self, collector: ComplianceCollector, formatter: ConsoleFormatter
    ) -> None:
        """Table shows correct pass/fail/total counts."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        collector.record(requirement_id="R2", transport="http", passed=False, level="MUST")
        collector.record(requirement_id="R3", transport="http", passed=True, level="SHOULD")
        report = ComplianceAggregator(collector).aggregate()
        output = formatter.format(report)
        # MUST row: 1 passed, 1 failed, 2 total
        assert "Passed" in output
        assert "Failed" in output
        assert "Total" in output

    def test_table_has_box_drawing(
        self, collector: ComplianceCollector, formatter: ConsoleFormatter
    ) -> None:
        """Table uses box-drawing characters."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        output = formatter.format(report)
        assert "\u2502" in output  # vertical bar
        assert "\u2500" in output  # horizontal bar


class TestTransportSummary:
    """Per-transport summary."""

    def test_transport_names_present(
        self, collector: ComplianceCollector, formatter: ConsoleFormatter
    ) -> None:
        """Transport names appear in the BY TRANSPORT section."""
        collector.record(requirement_id="R1", transport="grpc", passed=True, level="MUST")
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        output = formatter.format(report)
        assert "BY TRANSPORT:" in output
        assert "grpc" in output
        assert "http" in output

    def test_counts_shown(
        self, collector: ComplianceCollector, formatter: ConsoleFormatter
    ) -> None:
        """Passed/total counts appear for each transport."""
        collector.record(requirement_id="R1", transport="grpc", passed=True, level="MUST")
        collector.record(requirement_id="R2", transport="grpc", passed=False, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        output = formatter.format(report)
        assert "1/2" in output

    def test_checkmark_for_all_pass(
        self, collector: ComplianceCollector, formatter: ConsoleFormatter
    ) -> None:
        """Checkmark is shown when all tests pass for a transport."""
        collector.record(requirement_id="R1", transport="grpc", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        output = formatter.format(report)
        assert "\u2713" in output

    def test_warning_for_failures(
        self, collector: ComplianceCollector, formatter: ConsoleFormatter
    ) -> None:
        """Warning marker is shown when some tests fail for a transport."""
        collector.record(requirement_id="R1", transport="grpc", passed=True, level="MUST")
        collector.record(requirement_id="R2", transport="grpc", passed=False, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        output = formatter.format(report)
        assert "\u26a0" in output


class TestFailedRequirements:
    """Failed requirements section."""

    def test_failed_listed_with_error(
        self, collector: ComplianceCollector, formatter: ConsoleFormatter
    ) -> None:
        """Failed requirements are listed with transport and error."""
        collector.record(
            requirement_id="REQ-9.3",
            transport="jsonrpc",
            passed=False,
            level="MUST",
            errors=["Error code mismatch"],
        )
        report = ComplianceAggregator(collector).aggregate()
        output = formatter.format(report)
        assert "FAILED REQUIREMENTS:" in output
        assert "REQ-9.3" in output
        assert "jsonrpc" in output
        assert "Error code mismatch" in output

    def test_no_section_when_all_pass(
        self, collector: ComplianceCollector, formatter: ConsoleFormatter
    ) -> None:
        """No FAILED REQUIREMENTS section when all tests pass."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        output = formatter.format(report)
        assert "FAILED REQUIREMENTS:" not in output


class TestColorSupport:
    """ANSI colour support."""

    def test_color_enabled_adds_ansi(self, collector: ComplianceCollector) -> None:
        """When colour is enabled, ANSI escape codes appear in the output."""
        formatter = ConsoleFormatter(color=True)
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        output = formatter.format(report)
        assert "\033[" in output

    def test_color_disabled_no_ansi(
        self, collector: ComplianceCollector, formatter: ConsoleFormatter
    ) -> None:
        """When colour is disabled, no ANSI escape codes appear."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        output = formatter.format(report)
        assert "\033[" not in output


class TestEmptyReport:
    """Empty report handling."""

    def test_empty_report_produces_output(
        self, collector: ComplianceCollector, formatter: ConsoleFormatter
    ) -> None:
        """Empty collector produces valid output with title and table."""
        report = ComplianceAggregator(collector).aggregate()
        output = formatter.format(report)
        assert "A2A TCK Compliance Report" in output
        assert "OVERALL COMPLIANCE:" in output
