"""Console formatter for A2A TCK compatibility reports.

Transforms a :class:`CompatibilityReport` into a compact, human-readable
terminal summary with optional ANSI colour support.
"""

from __future__ import annotations

import sys

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from tck.reporting.aggregator import CompatibilityReport, RequirementResult


# -- ANSI helpers ------------------------------------------------------------

_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


_THRESHOLD_PERFECT = 100.0
_THRESHOLD_GOOD = 80.0


def _use_color() -> bool:
    """Return True when stdout is a TTY that likely supports colour."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


# -- Formatter ---------------------------------------------------------------


class ConsoleFormatter:
    """Formats a :class:`CompatibilityReport` as a concise terminal summary."""

    def __init__(self, *, sut_url: str = "", spec_version: str = "", color: bool | None = None) -> None:
        self._sut_url = sut_url
        self._spec_version = spec_version
        self._color = color if color is not None else _use_color()

    def format(self, report: CompatibilityReport) -> str:
        """Return a formatted console string."""
        lines: list[str] = []
        lines.append(self._header())
        lines.append(self._metadata(report))
        lines.append(self._overall(report))
        lines.append(self._level_table(report))
        lines.append(self._transport_summary(report))
        lines.append(self._failed_requirements(report))
        lines.append(self._manual_requirements(report))
        lines.append(self._rule())
        return "\n".join(lines) + "\n"

    # -- sections ------------------------------------------------------------

    def _header(self) -> str:
        rule = self._rule()
        title = "A2A TCK Compatibility Report"
        return f"{rule}\n{title:^55}\n{rule}"

    def _metadata(self, report: CompatibilityReport) -> str:
        parts = [f"SUT: {self._sut_url}"]
        if self._spec_version:
            parts.append(f"Spec Version: {self._spec_version}")
        parts.append(f"Timestamp: {report.timestamp}")
        return "\n".join(parts)

    def _overall(self, report: CompatibilityReport) -> str:
        value = f"{report.overall_compatibility:.1f}%"
        if self._color:
            if report.overall_compatibility == _THRESHOLD_PERFECT:
                value = f"{_GREEN}{_BOLD}{value}{_RESET}"
            elif report.overall_compatibility >= _THRESHOLD_GOOD:
                value = f"{_YELLOW}{_BOLD}{value}{_RESET}"
            else:
                value = f"{_RED}{_BOLD}{value}{_RESET}"
        return f"\nOVERALL COMPATIBILITY: {value} (automated checks)"

    def _level_table(self, report: CompatibilityReport) -> str:
        rows = [("Level", "Passed", "Failed", "Skipped", "Manual", "Total")]
        for level in ("MUST", "SHOULD", "MAY"):
            reqs = [r for r in report.per_requirement.values() if r.level == level]
            passed = sum(1 for r in reqs if r.status == "PASS")
            skipped = sum(1 for r in reqs if r.status == "SKIPPED")
            manual = sum(1 for r in reqs if r.status == "MANUAL")
            failed = len(reqs) - passed - skipped - manual
            rows.append(tuple(str(value) for value in (level, passed, failed, skipped, manual, len(reqs))))
        widths = [max(len(row[index]) for row in rows) + 2 for index in range(len(rows[0]))]

        def border(left: str, middle: str, right: str) -> str:
            return left + middle.join("─" * width for width in widths) + right

        lines = ["", border("┌", "┬", "┐")]
        for index, row in enumerate(rows):
            lines.append("│" + "│".join(f" {value:<{width - 2}} " for value, width in zip(row, widths, strict=True)) + "│")
            if index == 0:
                lines.append(border("├", "┼", "┤"))
        lines.append(border("└", "┴", "┘"))
        return "\n".join(lines)

    @staticmethod
    def _manual_requirements(report: CompatibilityReport) -> str:
        if not report.pending_manual:
            return ""
        lines = ["\nPENDING MANUAL VERIFICATION (excluded from automated scores):"]
        lines.extend(f"  {req_id} [{req.level}]: {req.description}" for req_id, req in report.pending_manual.items())
        return "\n".join(lines)

    def _transport_summary(self, report: CompatibilityReport) -> str:
        if not report.per_transport:
            return ""
        lines = ["\nBY TRANSPORT:"]
        for transport, t in report.per_transport.items():
            marker = self._transport_marker(t.passed, t.total - t.skipped)
            count = f"{t.passed}/{t.total}"
            if t.skipped > 0:
                count += f" ({t.skipped} skipped)"
            lines.append(f"  {transport + ':':<14} {count} {marker}")
        return "\n".join(lines)

    def _failed_requirements(self, report: CompatibilityReport) -> str:
        failed: dict[str, RequirementResult] = {
            req_id: req
            for req_id, req in report.per_requirement.items()
            if req.status == "FAIL"
        }
        if not failed:
            return ""

        lines = ["\nFAILED REQUIREMENTS:"]
        for req_id, req in failed.items():
            transports = ", ".join(
                t for t, s in req.transports.items() if s == "FAIL"
            )
            error = req.errors[0] if req.errors else "no details"
            marker = self._colorize("\u2717", _RED) if self._color else "\u2717"
            lines.append(f"  {marker} {req_id} ({transports}): {error}")
        return "\n".join(lines)

    # -- helpers -------------------------------------------------------------

    def _rule(self) -> str:
        return "\u2550" * 55

    def _transport_marker(self, passed: int, total: int) -> str:
        if passed == total:
            return self._colorize("\u2713", _GREEN) if self._color else "\u2713"
        return self._colorize("\u26a0", _YELLOW) if self._color else "\u26a0"

    @staticmethod
    def _colorize(text: str, color: str) -> str:
        return f"{color}{text}{_RESET}"
