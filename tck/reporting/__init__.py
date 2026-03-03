"""Reporting utilities for A2A TCK."""

from tck.reporting.aggregator import (
    ComplianceAggregator,
    ComplianceReport,
    RequirementResult,
    TransportResult,
)
from tck.reporting.collector import ComplianceCollector, TestResult


__all__ = [
    "ComplianceAggregator",
    "ComplianceCollector",
    "ComplianceReport",
    "RequirementResult",
    "TestResult",
    "TransportResult",
]
