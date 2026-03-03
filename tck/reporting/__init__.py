"""Reporting utilities for A2A TCK."""

from tck.reporting.aggregator import (
    ComplianceAggregator,
    ComplianceReport,
    RequirementResult,
    TransportResult,
)
from tck.reporting.collector import ComplianceCollector, TestResult
from tck.reporting.html_formatter import HTMLFormatter
from tck.reporting.json_formatter import JSONFormatter


__all__ = [
    "ComplianceAggregator",
    "ComplianceCollector",
    "ComplianceReport",
    "HTMLFormatter",
    "JSONFormatter",
    "RequirementResult",
    "TestResult",
    "TransportResult",
]
