"""Compliance aggregation for A2A TCK reports.

Takes raw results from a :class:`ComplianceCollector` and computes
compliance metrics broken down by requirement level and transport.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from tck.reporting.collector import ComplianceCollector, TestResult


@dataclass
class RequirementResult:
    """Aggregated result for a single requirement across transports."""

    level: str
    status: str
    transports: dict[str, str]
    errors: list[str] = field(default_factory=list)


@dataclass
class TransportResult:
    """Aggregated counts for a single transport."""

    total: int
    passed: int
    failed: int


@dataclass
class ComplianceReport:
    """Full compliance report produced by :class:`ComplianceAggregator`."""

    timestamp: str
    per_requirement: dict[str, RequirementResult]
    per_transport: dict[str, TransportResult]
    overall_compliance: float
    must_compliance: float
    should_compliance: float
    may_compliance: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to a plain dict suitable for JSON serialisation."""
        return asdict(self)


class ComplianceAggregator:
    """Computes compliance metrics from collected test results.

    A requirement *passes* only when it passes on **every** transport
    where it was tested.  Compliance for a given level is the percentage
    of requirements at that level which pass.  When no requirements exist
    for a level the compliance is 100.0 (nothing to fail).
    """

    def __init__(self, collector: ComplianceCollector) -> None:
        self._collector = collector

    def aggregate(self) -> ComplianceReport:
        """Build a complete :class:`ComplianceReport`."""
        per_requirement = self._compute_per_requirement()
        per_transport = self._compute_per_transport()

        return ComplianceReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            per_requirement=per_requirement,
            per_transport=per_transport,
            overall_compliance=self._compute_compliance(per_requirement, level=None),
            must_compliance=self._compute_compliance(per_requirement, level="MUST"),
            should_compliance=self._compute_compliance(per_requirement, level="SHOULD"),
            may_compliance=self._compute_compliance(per_requirement, level="MAY"),
        )

    def _compute_per_requirement(self) -> dict[str, RequirementResult]:
        grouped: dict[str, list[TestResult]] = defaultdict(list)
        for r in self._collector.get_results():
            grouped[r.requirement_id].append(r)

        out: dict[str, RequirementResult] = {}
        for req_id, results in grouped.items():
            transports: dict[str, str] = {}
            errors: list[str] = []
            for r in results:
                transports[r.transport] = "PASS" if r.passed else "FAIL"
                if not r.passed:
                    errors.extend(r.errors)

            all_passed = all(r.passed for r in results)
            out[req_id] = RequirementResult(
                level=results[0].level,
                status="PASS" if all_passed else "FAIL",
                transports=transports,
                errors=errors,
            )
        return out

    def _compute_per_transport(self) -> dict[str, TransportResult]:
        grouped: dict[str, list[TestResult]] = defaultdict(list)
        for r in self._collector.get_results():
            grouped[r.transport].append(r)

        out: dict[str, TransportResult] = {}
        for transport, results in grouped.items():
            passed = sum(1 for r in results if r.passed)
            out[transport] = TransportResult(
                total=len(results),
                passed=passed,
                failed=len(results) - passed,
            )
        return out

    @staticmethod
    def _compute_compliance(
        per_requirement: dict[str, RequirementResult],
        *,
        level: str | None,
    ) -> float:
        reqs = (
            per_requirement.values()
            if level is None
            else [r for r in per_requirement.values() if r.level == level]
        )
        reqs = list(reqs)
        if not reqs:
            return 100.0
        passing = sum(1 for r in reqs if r.status == "PASS")
        return (passing / len(reqs)) * 100.0
