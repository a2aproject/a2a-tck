"""Tests for the HTMLFormatter."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tck.reporting.aggregator import ComplianceAggregator
from tck.reporting.collector import ComplianceCollector
from tck.reporting.html_formatter import HTMLFormatter


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def collector() -> ComplianceCollector:
    """Return a fresh ComplianceCollector."""
    return ComplianceCollector()


@pytest.fixture
def formatter() -> HTMLFormatter:
    """Return an HTMLFormatter with test metadata."""
    return HTMLFormatter(sut_url="http://localhost:9999", spec_version="0.2.1")


class TestValidHTML:
    """Output is a valid HTML document."""

    def test_contains_doctype(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """Output starts with a DOCTYPE declaration."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert "<!DOCTYPE html>" in html

    def test_contains_html_tags(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """Output contains opening and closing html tags."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert "<html" in html
        assert "</html>" in html

    def test_empty_report_produces_valid_html(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """Empty collector produces valid HTML with empty table."""
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert "<!DOCTYPE html>" in html
        assert "<html" in html


class TestExecutiveSummary:
    """Executive summary section."""

    def test_compliance_percentages_present(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """Compliance percentages appear in the output."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert "100.0%" in html

    def test_sut_url_in_output(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """sut_url appears in the HTML output."""
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert "http://localhost:9999" in html

    def test_spec_version_in_output(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """spec_version appears in the HTML output."""
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert "0.2.1" in html


class TestPerRequirementTable:
    """Per-requirement table contents."""

    def test_requirement_ids_present(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """Requirement IDs appear in the table."""
        collector.record(requirement_id="REQ-3.1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert "REQ-3.1" in html

    def test_levels_present(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """Requirement levels appear in the table."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="SHOULD")
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert "SHOULD" in html

    def test_statuses_present(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """Requirement statuses appear in the table."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert "PASS" in html


class TestColorCoding:
    """PASS/FAIL cells use appropriate CSS classes."""

    def test_pass_uses_green(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """PASS cells have the 'pass' CSS class."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert 'class="pass"' in html

    def test_fail_uses_red(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """FAIL cells have the 'fail' CSS class."""
        collector.record(
            requirement_id="R1", transport="http", passed=False, level="MUST", errors=["err"]
        )
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert 'class="fail"' in html


class TestSkippedColorCoding:
    """Skipped cells use the 'skipped' CSS class."""

    def test_skipped_uses_grey(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """Skipped cells have the 'skipped' CSS class."""
        collector.record(
            requirement_id="R1", transport="http", passed=False, level="MUST", skipped=True
        )
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert 'class="skipped"' in html


class TestRequirementTooltip:
    """Requirement descriptions appear as tooltips."""

    def test_tooltip_from_registry(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """Known requirement IDs show their description as a title attribute."""
        collector.record(
            requirement_id="CORE-SEND-001", transport="http", passed=True, level="MUST"
        )
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert 'title="' in html
        assert "CORE-SEND-001" in html

    def test_no_tooltip_for_unknown_id(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """Unknown requirement IDs do not get a title attribute."""
        collector.record(
            requirement_id="UNKNOWN-999", transport="http", passed=True, level="MUST"
        )
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert "UNKNOWN-999" in html
        # The req ID cell should NOT have a title attribute
        assert 'title="' not in html


class TestErrorFormatting:
    """Errors are formatted as bullet lists with transport prefixes."""

    def test_errors_as_bullet_list(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """Errors appear in an unordered list."""
        collector.record(
            requirement_id="R1", transport="http", passed=False, level="MUST",
            errors=["timeout"],
        )
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert "<ul" in html
        assert "<li>" in html
        assert "timeout" in html

    def test_errors_prefixed_with_transport(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """Each error is prefixed with the transport that caused it."""
        collector.record(
            requirement_id="R1", transport="http", passed=False, level="MUST",
            errors=["connection refused"],
        )
        collector.record(
            requirement_id="R1", transport="grpc", passed=False, level="MUST",
            errors=["deadline exceeded"],
        )
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert "<strong>http</strong>: connection refused" in html
        assert "<strong>grpc</strong>: deadline exceeded" in html


class TestPerTransportSummary:
    """Per-transport summary section."""

    def test_transport_names_present(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """Transport names appear in the summary."""
        collector.record(requirement_id="R1", transport="grpc", passed=True, level="MUST")
        collector.record(requirement_id="R2", transport="http", passed=False, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert "grpc" in html
        assert "http" in html

    def test_counts_present(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """Passed, failed, and total counts appear in the summary."""
        collector.record(requirement_id="R1", transport="grpc", passed=True, level="MUST")
        collector.record(requirement_id="R2", transport="grpc", passed=False, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert ">1<" in html
        assert ">2<" in html


class TestFailedTests:
    """Failed tests section."""

    def test_only_failed_requirements_listed(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """Only failed requirements appear in the failed tests list."""
        collector.record(requirement_id="R-OK", transport="http", passed=True, level="MUST")
        collector.record(
            requirement_id="R-BAD",
            transport="http",
            passed=False,
            level="MUST",
            errors=["timeout"],
        )
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        failed_section = html[html.index("Failed Tests") :]
        assert "R-BAD" in failed_section
        assert "timeout" in failed_section
        li_section = failed_section[failed_section.index("<ul>") :]
        assert "R-OK" not in li_section

    def test_no_failures_shows_message(
        self, collector: ComplianceCollector, formatter: HTMLFormatter
    ) -> None:
        """When all tests pass, a 'No failures' message is shown."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        html = formatter.format(report)
        assert "No failures" in html


class TestWriteFile:
    """write() creates a file at the given path."""

    def test_write_creates_file(
        self, collector: ComplianceCollector, formatter: HTMLFormatter, tmp_path: Path
    ) -> None:
        """write() creates parent dirs and writes valid HTML."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        out = tmp_path / "reports" / "compliance.html"
        formatter.write(report, out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
