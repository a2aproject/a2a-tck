"""Compliance result collector for A2A TCK tests.

Aggregates test results during execution and provides grouping
by requirement and transport for downstream reporting.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class TestResult:
    """A single test result recorded during TCK execution."""

    requirement_id: str
    transport: str
    passed: bool
    errors: list[str] = field(default_factory=list)
    level: Literal["MUST", "SHOULD", "MAY"] = "MUST"


class ComplianceCollector:
    """Collects and aggregates compliance test results.

    Used as a session-scoped pytest fixture.  Tests call :meth:`record` to
    store individual results; the reporting layer later queries grouped
    views via :meth:`get_per_requirement` and :meth:`get_per_transport`.
    """

    def __init__(self) -> None:
        self._results: list[TestResult] = []

    def record(
        self,
        *,
        requirement_id: str,
        transport: str,
        passed: bool,
        errors: list[str] | None = None,
        level: str = "MUST",
    ) -> None:
        """Record a single test result."""
        self._results.append(
            TestResult(
                requirement_id=requirement_id,
                transport=transport,
                passed=passed,
                errors=errors or [],
                level=level,  # type: ignore[arg-type]
            )
        )

    def get_results(self) -> list[TestResult]:
        """Return all recorded results."""
        return list(self._results)

    def get_per_requirement(self) -> dict[str, dict[str, str]]:
        """Group results by requirement ID.

        Returns a mapping of ``requirement_id`` to a dict with:
        - ``level``: the requirement level (MUST/SHOULD/MAY)
        - ``status``: ``"PASS"`` if all results passed, else ``"FAIL"``
        - ``transports``: comma-separated list of transports tested
        """
        grouped: dict[str, list[TestResult]] = defaultdict(list)
        for r in self._results:
            grouped[r.requirement_id].append(r)

        out: dict[str, dict[str, str]] = {}
        for req_id, results in grouped.items():
            all_passed = all(r.passed for r in results)
            transports = sorted({r.transport for r in results})
            out[req_id] = {
                "level": results[0].level,
                "status": "PASS" if all_passed else "FAIL",
                "transports": ", ".join(transports),
            }
        return out

    def get_per_transport(self) -> dict[str, dict[str, int]]:
        """Group results by transport.

        Returns a mapping of ``transport`` to a dict with:
        - ``total``: total number of results
        - ``passed``: number of passing results
        - ``failed``: number of failing results
        """
        grouped: dict[str, list[TestResult]] = defaultdict(list)
        for r in self._results:
            grouped[r.transport].append(r)

        out: dict[str, dict[str, int]] = {}
        for transport, results in grouped.items():
            passed = sum(1 for r in results if r.passed)
            out[transport] = {
                "total": len(results),
                "passed": passed,
                "failed": len(results) - passed,
            }
        return out

    def reset(self) -> None:
        """Clear all stored results."""
        self._results.clear()
