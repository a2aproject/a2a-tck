"""Reporting utilities for A2A TCK."""

from tck.reporting.aggregator import (
    CompatibilityAggregator,
    CompatibilityReport,
    RequirementResult,
    TransportResult,
)
from tck.reporting.collector import CompatibilityCollector, TestResult
from tck.reporting.console_formatter import ConsoleFormatter
from tck.reporting.html_formatter import HTMLFormatter
from tck.reporting.json_formatter import JSONFormatter


__all__ = [
    "CompatibilityAggregator",
    "CompatibilityCollector",
    "CompatibilityReport",
    "ConsoleFormatter",
    "HTMLFormatter",
    "JSONFormatter",
    "RequirementResult",
    "TestResult",
    "TransportResult",
]
