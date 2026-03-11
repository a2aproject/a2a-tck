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
    description: str = ""
    spec_url: str = ""
    transport_errors: dict[str, list[str]] = field(default_factory=dict)
    test_ids: list[str] = field(default_factory=list)


@dataclass
class TransportResult:
    """Aggregated counts for a single transport."""

    total: int
    passed: int
    failed: int
    skipped: int = 0


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
    agent_card: dict[str, Any] = field(default_factory=dict)

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

    def __init__(
        self,
        collector: ComplianceCollector,
        *,
        agent_card: dict[str, Any] | None = None,
    ) -> None:
        self._collector = collector
        self._agent_card = agent_card or {}

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
            agent_card=self._agent_card,
        )

    def _compute_per_requirement(self) -> dict[str, RequirementResult]:
        grouped: dict[str, list[TestResult]] = defaultdict(list)
        for r in self._collector.get_results():
            grouped[r.requirement_id].append(r)

        out: dict[str, RequirementResult] = {}
        for req_id, results in grouped.items():
            transports: dict[str, str] = {}
            errors: list[str] = []
            transport_errors: dict[str, list[str]] = {}
            for r in results:
                if r.skipped:
                    transports[r.transport] = "SKIPPED"
                elif r.passed:
                    transports[r.transport] = "PASS"
                else:
                    transports[r.transport] = "FAIL"
                    errors.extend(r.errors)
                    if r.errors:
                        transport_errors.setdefault(r.transport, []).extend(
                            r.errors
                        )

            any_failed = any(not r.passed and not r.skipped for r in results)
            all_skipped = all(r.skipped for r in results)
            if any_failed:
                status = "FAIL"
            elif all_skipped:
                status = "SKIPPED"
            else:
                status = "PASS"

            description = ""
            spec_url = ""
            try:
                from tck.requirements.registry import get_requirement_by_id

                spec = get_requirement_by_id(req_id)
                description = spec.description
                spec_url = spec.spec_url
            except (KeyError, ImportError):
                pass

            test_ids = sorted({r.test_id for r in results if r.test_id})

            out[req_id] = RequirementResult(
                level=results[0].level,
                status=status,
                transports=transports,
                errors=errors,
                description=description,
                spec_url=spec_url,
                transport_errors=transport_errors,
                test_ids=test_ids,
            )

        self._add_untested_requirements(out)
        return out

    @staticmethod
    def _add_untested_requirements(out: dict[str, RequirementResult]) -> None:
        """Add registry requirements that were never tested."""
        try:
            from tck.requirements.registry import ALL_REQUIREMENTS

            for spec in ALL_REQUIREMENTS:
                if spec.id not in out:
                    out[spec.id] = RequirementResult(
                        level=spec.level.value,
                        status="NOT TESTED",
                        transports={},
                        description=spec.description,
                        spec_url=spec.spec_url,
                    )
        except ImportError:
            pass

    def _compute_per_transport(self) -> dict[str, TransportResult]:
        grouped: dict[str, list[TestResult]] = defaultdict(list)
        for r in self._collector.get_results():
            grouped[r.transport].append(r)

        out: dict[str, TransportResult] = {}
        for transport, results in grouped.items():
            passed = sum(1 for r in results if r.passed and not r.skipped)
            skipped = sum(1 for r in results if r.skipped)
            out[transport] = TransportResult(
                total=len(results),
                passed=passed,
                failed=len(results) - passed - skipped,
                skipped=skipped,
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
        reqs = [r for r in reqs if r.status not in ("SKIPPED", "NOT TESTED")]
        if not reqs:
            return 100.0
        passing = sum(1 for r in reqs if r.status == "PASS")
        return (passing / len(reqs)) * 100.0
