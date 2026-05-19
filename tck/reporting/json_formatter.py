"""JSON formatter for A2A TCK compatibility reports.

Transforms a :class:`CompatibilityReport` into the PRD-specified JSON
structure and optionally writes it to disk.
"""

from __future__ import annotations

import json

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from pathlib import Path

    from tck.reporting.aggregator import CompatibilityReport


class JSONFormatter:
    """Formats a :class:`CompatibilityReport` as PRD-compliant JSON."""

    def __init__(self, *, sut_url: str = "", spec_version: str = "") -> None:
        self._sut_url = sut_url
        self._spec_version = spec_version

    def format(self, report: CompatibilityReport) -> str:
        """Return an indented JSON string matching the PRD output structure."""
        data = self._build_dict(report)
        return json.dumps(data, indent=2)

    def write(self, report: CompatibilityReport, path: Path) -> None:
        """Write the JSON report to *path*, creating parent directories."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.format(report), encoding="utf-8")

    def _build_dict(self, report: CompatibilityReport) -> dict[str, Any]:
        data: dict[str, Any] = {
            "summary": {
                "timestamp": report.timestamp,
                "sut_url": self._sut_url,
                "spec_version": self._spec_version,
                "overall_compatibility": self._format_compatibility(report.overall_compatibility),
                "must_compatibility": self._format_compatibility(report.must_compatibility),
                "should_compatibility": self._format_compatibility(report.should_compatibility),
                "may_compatibility": self._format_compatibility(report.may_compatibility),
            },
            "per_requirement": {
                req_id: {
                    "level": req.level,
                    "status": req.status,
                    "transports": dict(req.transports),
                    "errors": list(req.errors),
                    "test_ids": list(req.test_ids),
                }
                for req_id, req in report.per_requirement.items()
            },
            "per_transport": {
                transport: {
                    "total": t.total,
                    "passed": t.passed,
                    "failed": t.failed,
                    "skipped": t.skipped,
                }
                for transport, t in report.per_transport.items()
            },
        }
        if report.agent_card:
            data["agent_card"] = report.agent_card
        return data

    @staticmethod
    def _format_compatibility(value: float) -> str:
        return f"{value:.1f}%"
