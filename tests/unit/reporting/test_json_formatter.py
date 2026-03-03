"""Tests for the JSONFormatter."""

from __future__ import annotations

import json

from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from tck.reporting.aggregator import ComplianceAggregator
from tck.reporting.collector import ComplianceCollector
from tck.reporting.json_formatter import JSONFormatter


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def collector() -> ComplianceCollector:
    """Return a fresh ComplianceCollector."""
    return ComplianceCollector()


@pytest.fixture
def formatter() -> JSONFormatter:
    """Return a JSONFormatter with test metadata."""
    return JSONFormatter(sut_url="http://localhost:9999", spec_version="0.2.1")


class TestValidJSON:
    """Output is valid, parseable JSON."""

    def test_output_is_valid_json(
        self, collector: ComplianceCollector, formatter: JSONFormatter
    ) -> None:
        """Formatted output is parseable as JSON."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        result = json.loads(formatter.format(report))
        assert isinstance(result, dict)

    def test_empty_report_is_valid_json(
        self, collector: ComplianceCollector, formatter: JSONFormatter
    ) -> None:
        """Empty collector produces valid JSON with empty sections."""
        report = ComplianceAggregator(collector).aggregate()
        result = json.loads(formatter.format(report))
        assert isinstance(result, dict)
        assert result["per_requirement"] == {}
        assert result["per_transport"] == {}


class TestSummary:
    """Summary section structure and values."""

    def test_timestamp_is_iso8601(
        self, collector: ComplianceCollector, formatter: JSONFormatter
    ) -> None:
        """Timestamp in summary is a valid ISO 8601 string."""
        report = ComplianceAggregator(collector).aggregate()
        data = json.loads(formatter.format(report))
        # Should parse without error
        datetime.fromisoformat(data["summary"]["timestamp"])

    def test_compliance_are_percentage_strings(
        self, collector: ComplianceCollector, formatter: JSONFormatter
    ) -> None:
        """Compliance values are strings ending with '%'."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        data = json.loads(formatter.format(report))
        summary = data["summary"]
        for key in ("overall_compliance", "must_compliance", "should_compliance", "may_compliance"):
            assert isinstance(summary[key], str)
            assert summary[key].endswith("%")

    def test_sut_url_in_summary(
        self, collector: ComplianceCollector, formatter: JSONFormatter
    ) -> None:
        """sut_url appears in summary with the configured value."""
        report = ComplianceAggregator(collector).aggregate()
        data = json.loads(formatter.format(report))
        assert data["summary"]["sut_url"] == "http://localhost:9999"

    def test_spec_version_in_summary(
        self, collector: ComplianceCollector, formatter: JSONFormatter
    ) -> None:
        """spec_version appears in summary with the configured value."""
        report = ComplianceAggregator(collector).aggregate()
        data = json.loads(formatter.format(report))
        assert data["summary"]["spec_version"] == "0.2.1"


class TestPerRequirement:
    """per_requirement section structure."""

    def test_requirement_structure(
        self, collector: ComplianceCollector, formatter: JSONFormatter
    ) -> None:
        """Each requirement has level, status, transports dict, and errors."""
        collector.record(requirement_id="REQ-3.1", transport="grpc", passed=True, level="MUST")
        collector.record(
            requirement_id="REQ-3.1",
            transport="http",
            passed=False,
            level="MUST",
            errors=["bad status"],
        )
        report = ComplianceAggregator(collector).aggregate()
        data = json.loads(formatter.format(report))
        req = data["per_requirement"]["REQ-3.1"]
        assert req["level"] == "MUST"
        assert req["status"] == "FAIL"
        assert req["transports"] == {"grpc": "PASS", "http": "FAIL"}
        assert req["errors"] == ["bad status"]


class TestPerTransport:
    """per_transport section structure."""

    def test_transport_structure(
        self, collector: ComplianceCollector, formatter: JSONFormatter
    ) -> None:
        """Each transport has total, passed, and failed as integers."""
        collector.record(requirement_id="R1", transport="grpc", passed=True, level="MUST")
        collector.record(requirement_id="R2", transport="grpc", passed=False, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        data = json.loads(formatter.format(report))
        grpc = data["per_transport"]["grpc"]
        expected_total = 2
        assert grpc["total"] == expected_total
        assert grpc["passed"] == 1
        assert grpc["failed"] == 1
        assert all(isinstance(v, int) for v in grpc.values())


class TestWriteFile:
    """write() creates a file at the given path."""

    def test_write_creates_file(
        self, collector: ComplianceCollector, formatter: JSONFormatter, tmp_path: Path
    ) -> None:
        """write() creates parent dirs and writes valid JSON."""
        collector.record(requirement_id="R1", transport="http", passed=True, level="MUST")
        report = ComplianceAggregator(collector).aggregate()
        out = tmp_path / "reports" / "compliance.json"
        formatter.write(report, out)
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "summary" in data
        assert "per_requirement" in data
        assert "per_transport" in data
