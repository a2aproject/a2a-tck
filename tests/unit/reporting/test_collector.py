"""Tests for ComplianceCollector.record_count."""

from __future__ import annotations

import pytest

from tck.reporting.collector import ComplianceCollector


TWO = 2


@pytest.fixture
def collector() -> ComplianceCollector:
    """Return a fresh ComplianceCollector."""
    return ComplianceCollector()


class TestRecordCount:
    """record_count tracks calls to record()."""

    def test_starts_at_zero(self, collector: ComplianceCollector) -> None:
        """Fresh collector has a zero record count."""
        assert collector.record_count == 0

    def test_increments_on_record(self, collector: ComplianceCollector) -> None:
        """Each call to record() increments the counter."""
        collector.record(
            requirement_id="CORE-GET-001",
            transport="jsonrpc",
            passed=True,
        )
        assert collector.record_count == 1

        collector.record(
            requirement_id="CORE-GET-002",
            transport="grpc",
            passed=False,
            errors=["boom"],
        )
        assert collector.record_count == TWO

    def test_reset_clears_count(self, collector: ComplianceCollector) -> None:
        """reset() zeroes the record count."""
        collector.record(
            requirement_id="CORE-GET-001",
            transport="jsonrpc",
            passed=True,
        )
        assert collector.record_count == 1
        collector.reset()
        assert collector.record_count == 0
