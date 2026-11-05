"""Compatibility aggregation for A2A TCK reports.

Takes raw results from a :class:`CompatibilityCollector` and computes
compatibility metrics broken down by requirement level and transport.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from tck.reporting.collector import summarize_status
from tck.requirements.tags import NOT_AUTOMATABLE


if TYPE_CHECKING:
    from tck.reporting.collector import CompatibilityCollector, TestResult


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
class CompatibilityReport:
    """Full compatibility report produced by :class:`CompatibilityAggregator`."""

    timestamp: str
    per_requirement: dict[str, RequirementResult]
    per_transport: dict[str, TransportResult]
    overall_compatibility: float
    must_compatibility: float
    should_compatibility: float
    may_compatibility: float
    agent_card: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a plain dict suitable for JSON serialisation."""
        data = asdict(self)
        data["score_scope"] = "automated"
        data["manual_verification_required"] = list(self.pending_manual)
        return data

    @property
    def pending_manual(self) -> dict[str, RequirementResult]:
        """Manual obligations with no recorded verification, never automatic passes."""
        return {req_id: req for req_id, req in self.per_requirement.items() if req.status == "MANUAL"}


class CompatibilityAggregator:
    """Computes compatibility metrics from collected test results.

    A requirement *passes* only when it passes on **every** transport
    where it was tested.  Compatibility for a given level is the percentage
    of requirements at that level which pass.  When no requirements exist
    for a level the compatibility is 100.0 (nothing to fail).

    A requirement that was registered but never exercised (``NOT TESTED`` —
    e.g. the SUT never responded, or crashed before the test ran) counts
    against compatibility the same as a failure would: it is *not* excluded
    from the automated denominator. ``MANUAL`` obligations are reported
    separately and require manual verification; they are never automatic passes.
    ``SKIPPED`` requirements (legitimately
    inapplicable to this SUT, e.g. an optional capability it doesn't
    implement) are also excluded. Otherwise an unreachable SUT that answers zero
    requests can report 100% compatibility on the handful of requirements
    that happened to produce a result before every other one silently
    dropped out of the denominator as "not tested".
    """

    def __init__(
        self,
        collector: CompatibilityCollector,
        *,
        agent_card: dict[str, Any] | None = None,
    ) -> None:
        self._collector = collector
        self._agent_card = agent_card or {}

    def aggregate(self) -> CompatibilityReport:
        """Build a complete :class:`CompatibilityReport`."""
        per_requirement = self._compute_per_requirement()
        per_transport = self._compute_per_transport()

        return CompatibilityReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            per_requirement=per_requirement,
            per_transport=per_transport,
            overall_compatibility=self._compute_compatibility(per_requirement, level=None),
            must_compatibility=self._compute_compatibility(per_requirement, level="MUST"),
            should_compatibility=self._compute_compatibility(per_requirement, level="SHOULD"),
            may_compatibility=self._compute_compatibility(per_requirement, level="MAY"),
            agent_card=self._agent_card,
        )

    def _compute_per_requirement(self) -> dict[str, RequirementResult]:
        grouped: dict[str, list[TestResult]] = defaultdict(list)
        for r in self._collector.get_results():
            grouped[r.requirement_id].append(r)

        out: dict[str, RequirementResult] = {}
        for req_id, results in grouped.items():
            by_transport: dict[str, list[TestResult]] = defaultdict(list)
            errors: list[str] = []
            transport_errors: dict[str, list[str]] = {}
            for result in results:
                by_transport[result.transport].append(result)
                if not result.passed and not result.skipped:
                    errors.extend(result.errors)
                    if result.errors:
                        transport_errors.setdefault(result.transport, []).extend(result.errors)
            transports = {transport: summarize_status(values) for transport, values in by_transport.items()}
            status = summarize_status(results)

            description = ""
            spec_url = ""
            try:
                from tck.requirements.registry import get_requirement_by_id

                spec = get_requirement_by_id(req_id)
                description = spec.description
                spec_url = spec.spec_url
            except KeyError:
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
        from tck.requirements.registry import ALL_REQUIREMENTS

        for spec in ALL_REQUIREMENTS:
            if spec.id not in out:
                out[spec.id] = RequirementResult(
                    level=spec.level.value,
                    status="MANUAL" if NOT_AUTOMATABLE in spec.tags else "NOT TESTED",
                    transports={},
                    description=spec.description,
                    spec_url=spec.spec_url,
                )

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
    def _compute_compatibility(
        per_requirement: dict[str, RequirementResult],
        *,
        level: str | None,
    ) -> float:
        reqs = (
            per_requirement.values()
            if level is None
            else [r for r in per_requirement.values() if r.level == level]
        )
        reqs = [r for r in reqs if r.status not in {"SKIPPED", "MANUAL"}]
        if not reqs:
            return 100.0
        passing = sum(1 for r in reqs if r.status == "PASS")
        return (passing / len(reqs)) * 100.0
