"""Compatibility result collector for A2A TCK tests.

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
    skipped: bool = False
    test_id: str = ""


class CompatibilityCollector:
    """Collects and aggregates compatibility test results.

    Used as a session-scoped pytest fixture.  Tests call :meth:`record` to
    store individual results; the reporting layer later queries grouped
    views via :meth:`get_per_requirement` and :meth:`get_per_transport`.
    """

    def __init__(self) -> None:
        self._results: list[TestResult] = []
        self._record_count: int = 0

    def record(
        self,
        *,
        requirement_id: str,
        transport: str,
        passed: bool,
        errors: list[str] | None = None,
        level: str = "MUST",
        skipped: bool = False,
        test_id: str = "",
    ) -> None:
        """Record a single test result."""
        if not test_id:
            test_id = _infer_test_id()
        self._results.append(
            TestResult(
                requirement_id=requirement_id,
                transport=transport,
                passed=passed,
                errors=errors or [],
                level=level,  # type: ignore[arg-type]
                skipped=skipped,
                test_id=test_id,
            )
        )
        self._record_count += 1

    @property
    def record_count(self) -> int:
        """Return the number of results recorded so far."""
        return self._record_count

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
            any_failed = any(not r.passed and not r.skipped for r in results)
            all_skipped = all(r.skipped for r in results)
            transports = sorted({r.transport for r in results})
            if any_failed:
                status = "FAIL"
            elif all_skipped:
                status = "SKIPPED"
            else:
                status = "PASS"
            out[req_id] = {
                "level": results[0].level,
                "status": status,
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
            passed = sum(1 for r in results if r.passed and not r.skipped)
            skipped = sum(1 for r in results if r.skipped)
            out[transport] = {
                "total": len(results),
                "passed": passed,
                "failed": len(results) - passed - skipped,
                "skipped": skipped,
            }
        return out

    def reset(self) -> None:
        """Clear all stored results."""
        self._results.clear()
        self._record_count = 0


def _infer_test_id() -> str:
    """Walk the call stack to find the outermost ``test_*`` function.

    Returns a pytest-style node ID (``relative/path.py::ClassName::method``)
    or an empty string when called outside a test context.
    """
    import inspect
    import os

    # Walk outward from the caller of record() looking for test frames.
    best: tuple[str, str, str | None] = ("", "", None)
    for frame_info in inspect.stack():
        func_name = frame_info.function
        if not func_name.startswith("test_"):
            continue
        filename = frame_info.filename
        # Prefer paths relative to the project root.
        try:
            rel = os.path.relpath(filename)
        except ValueError:
            rel = filename
        # Try to extract the class name from the frame's locals.
        cls_name: str | None = None
        local_self = frame_info.frame.f_locals.get("self")
        if local_self is not None:
            cls_name = type(local_self).__name__
        best = (rel, func_name, cls_name)

    if not best[0]:
        return ""
    path, func, cls = best
    if cls:
        return f"{path}::{cls}::{func}"
    return f"{path}::{func}"
