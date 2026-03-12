"""Tests for the HTMLFormatter."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tck.reporting.aggregator import CompatibilityAggregator
from tck.reporting.collector import CompatibilityCollector
from tck.reporting.html_formatter import HTMLFormatter


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def collector() -> CompatibilityCollector:
    """Return a fresh CompatibilityCollector."""
    return CompatibilityCollector()


@pytest.fixture
def agent_card() -> dict:
    """Return a minimal agent card with required fields."""
    return {"name": "TestAgent", "version": "1.0.0"}


@pytest.fixture
def formatter() -> HTMLFormatter:
    """Return an HTMLFormatter with test metadata."""
    return HTMLFormatter(sut_url="http://localhost:9999")


class TestValidHTML:
    """Output is a valid HTML document."""

    def test_contains_doctype(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """Output starts with a DOCTYPE declaration."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert "<!DOCTYPE html>" in html

    def test_contains_html_tags(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """Output contains opening and closing html tags."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert "<html" in html
        assert "</html>" in html

    def test_empty_report_produces_valid_html(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """Empty collector produces valid HTML with empty table."""
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert "<!DOCTYPE html>" in html
        assert "<html" in html


class TestExecutiveSummary:
    """Executive summary section."""

    def test_compatibility_percentages_present(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """Compatibility percentages appear in the output."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert "100.0%" in html

    def test_sut_url_in_output(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """sut_url appears in the HTML output."""
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert "http://localhost:9999" in html

class TestPerRequirementTable:
    """Per-requirement table contents."""

    def test_requirement_ids_present(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """Requirement IDs appear in the table."""
        collector.record(requirement_id="REQ-3.1", transport="http", passed=True, level="MUST")
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert "REQ-3.1" in html

    def test_levels_present(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """Requirement levels appear in the table."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="SHOULD")
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert "SHOULD" in html

    def test_statuses_present(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """Requirement statuses appear in the table."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert "PASS" in html


class TestColorCoding:
    """PASS/FAIL cells use appropriate CSS classes."""

    def test_pass_uses_green(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """PASS cells have the 'pass' CSS class."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert 'class="pass"' in html

    def test_fail_uses_red(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """FAIL cells have the 'fail' CSS class."""
        collector.record(
            requirement_id="R1", transport="http", passed=False, level="MUST", errors=["err"]
        )
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert 'class="fail"' in html


class TestSkippedColorCoding:
    """Skipped cells use the 'skipped' CSS class."""

    def test_skipped_uses_grey(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """Skipped cells have the 'skipped' CSS class."""
        collector.record(
            requirement_id="R1", transport="http", passed=False, level="MUST", skipped=True
        )
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert 'class="skipped"' in html


class TestSpecUrlLink:
    """Requirement IDs link to the specification when spec_url is available."""

    def test_known_requirement_links_to_spec(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """Known requirement IDs are rendered as links to the GitHub specification."""
        collector.record(
            requirement_id="CORE-SEND-001", transport="http", passed=True, level="MUST"
        )
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert "github.com/a2aproject/A2A/blob/" in html
        assert "/docs/specification.md#311-send-message" in html
        assert "CORE-SEND-001</a>" in html

    def test_unknown_requirement_has_no_link(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """Unknown requirement IDs are not rendered as links."""
        collector.record(
            requirement_id="UNKNOWN-999", transport="http", passed=True, level="MUST"
        )
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert "UNKNOWN-999" in html
        assert "href" not in html.split("UNKNOWN-999")[0].split("<td")[-1]


class TestTestIdColumn:
    """Test IDs appear in the per-requirement table."""

    def test_test_id_column_header(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """The per-requirement table has a Test column header."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert "<th>Test</th>" in html

    def test_test_id_in_row(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """Test IDs appear in the row when recorded."""
        collector.record(
            requirement_id="R1", transport="http", passed=True, level="MUST",
            test_id="tests/test_example.py::TestFoo::test_bar",
        )
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert "TestFoo::test_bar" in html
        assert 'class="test-id"' in html
        assert 'href="tck_report.html#tests/test_example.py::TestFoo::test_bar"' in html

    def test_auto_inferred_test_id(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """Test IDs are auto-inferred from the call stack."""
        # This test itself is the caller, so the inferred ID should contain
        # this test's method name.
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        req = report.per_requirement["R1"]
        assert any("test_auto_inferred_test_id" in tid for tid in req.test_ids)


class TestErrorFormatting:
    """Errors are formatted as bullet lists with transport prefixes."""

    def test_errors_as_bullet_list(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """Errors appear in an unordered list."""
        collector.record(
            requirement_id="R1", transport="http", passed=False, level="MUST",
            errors=["timeout"],
        )
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert "<ul" in html
        assert "<li>" in html
        assert "timeout" in html

    def test_errors_prefixed_with_transport(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
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
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert "<strong>http</strong>: connection refused" in html
        assert "<strong>grpc</strong>: deadline exceeded" in html


class TestPerTransportSummary:
    """Per-transport summary section."""

    def test_transport_names_present(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """Transport names appear in the summary."""
        collector.record(requirement_id="R1", transport="grpc", passed=True, level="MUST")
        collector.record(requirement_id="R2", transport="http", passed=False, level="MUST")
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert "grpc" in html
        assert "http" in html

    def test_counts_present(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """Passed, failed, and total counts appear in the summary."""
        collector.record(requirement_id="R1", transport="grpc", passed=True, level="MUST")
        collector.record(requirement_id="R2", transport="grpc", passed=False, level="MUST")
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert ">1<" in html
        assert ">2<" in html


class TestFailedTests:
    """Failed tests section."""

    def test_only_failed_requirements_listed(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
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
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        failed_section = html[html.index("Failed Tests") :]
        assert "R-BAD" in failed_section
        assert "timeout" in failed_section
        li_section = failed_section[failed_section.index("<ul>") :]
        assert "R-OK" not in li_section

    def test_no_failures_shows_message(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """When all tests pass, a 'No failures' message is shown."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert "No failures" in html


class TestAgentCardSection:
    """Agent card section in HTML report."""

    def test_agent_card_rendered(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter
    ) -> None:
        """Agent card JSON appears in the report when provided."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        html = formatter.format(report)
        assert "Agent Card" in html
        assert "TestAgent" in html
        assert "1.0" in html
        assert "<details>" in html

class TestWriteFile:
    """write() creates a file at the given path."""

    def test_write_creates_file(
        self, collector: CompatibilityCollector, agent_card: dict, formatter: HTMLFormatter, tmp_path: Path
    ) -> None:
        """write() creates parent dirs and writes valid HTML."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = CompatibilityAggregator(collector, agent_card=agent_card).aggregate()
        out = tmp_path / "reports" / "compatibility.html"
        formatter.write(report, out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
