"""HTML formatter for A2A TCK compliance reports.

Transforms a :class:`ComplianceReport` into a self-contained HTML
document with inline CSS and optionally writes it to disk.
"""

from __future__ import annotations

import json

from html import escape
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path

    from tck.reporting.aggregator import ComplianceReport, RequirementResult


class HTMLFormatter:
    """Formats a :class:`ComplianceReport` as a self-contained HTML page."""

    def __init__(self, *, sut_url: str = "") -> None:
        self._sut_url = sut_url

    def format(self, report: ComplianceReport) -> str:
        """Return a complete HTML document string."""
        return (
            "<!DOCTYPE html>\n"
            "<html lang=\"en\">\n"
            "<head>\n"
            '<meta charset="utf-8">\n'
            "<title>A2A TCK Compliance Report</title>\n"
            f"<style>{_CSS}</style>\n"
            "</head>\n"
            "<body>\n"
            f"{self._render_executive_summary(report)}"
            f"{self._render_agent_card(report)}"
            f"{self._render_per_requirement_table(report)}"
            f"{self._render_per_transport_summary(report)}"
            f"{self._render_failed_tests(report)}"
            "</body>\n"
            "</html>\n"
        )

    def write(self, report: ComplianceReport, path: Path) -> None:
        """Write the HTML report to *path*, creating parent directories."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.format(report), encoding="utf-8")

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def _render_executive_summary(self, report: ComplianceReport) -> str:
        return (
            '<div class="section">\n'
            "<h1>Executive Summary</h1>\n"
            f'<div class="overall">{_format_compliance(report.overall_compliance)}</div>\n'
            '<table class="summary-table">\n'
            "<tr><th>Level</th><th>Compliance</th></tr>\n"
            f"<tr><td>MUST</td><td>{_format_compliance(report.must_compliance)}</td></tr>\n"
            f"<tr><td>SHOULD</td><td>{_format_compliance(report.should_compliance)}</td></tr>\n"
            f"<tr><td>MAY</td><td>{_format_compliance(report.may_compliance)}</td></tr>\n"
            "</table>\n"
            f"<p>Timestamp: {escape(report.timestamp)}</p>\n"
            f'<p>SUT URL: <a href="{escape(self._sut_url)}">{escape(self._sut_url)}</a></p>\n'
            f"<p>SUT Version: {escape(report.agent_card['version'])}</p>\n"
            "</div>\n"
        )

    @staticmethod
    def _render_agent_card(report: ComplianceReport) -> str:
        card_json = json.dumps(report.agent_card, indent=2)
        return (
            '<div class="section">\n'
            "<details>\n"
            "<summary><h2 style=\"display:inline\">Agent Card</h2></summary>\n"
            f'<pre class="agent-card">{escape(card_json)}</pre>\n'
            "</details>\n"
            "</div>\n"
        )

    def _render_per_requirement_table(self, report: ComplianceReport) -> str:
        transports = sorted(report.per_transport)
        header_cells = "".join(f"<th>{escape(t)}</th>" for t in transports)
        header = (
            "<tr>"
            "<th>Requirement</th>"
            "<th>Level</th>"
            "<th>Status</th>"
            f"{header_cells}"
            "<th>Test</th>"
            "<th>Errors</th>"
            "</tr>\n"
        )

        rows = ""
        for req_id, req in report.per_requirement.items():
            rows += self._render_requirement_row(req_id, req, transports)

        return (
            '<div class="section">\n'
            "<h2>Per-Requirement Results</h2>\n"
            '<table class="req-table">\n'
            f"{header}"
            f"{rows}"
            "</table>\n"
            "</div>\n"
        )

    @staticmethod
    def _render_requirement_row(
        req_id: str, req: RequirementResult, transports: list[str]
    ) -> str:
        if req.status == "PASS":
            status_class = "pass"
        elif req.status == "SKIPPED":
            status_class = "skipped"
        else:
            status_class = "fail"
        transport_cells = ""
        for t in transports:
            result = req.transports.get(t, "")
            cell_class = ""
            if result == "PASS":
                cell_class = ' class="pass"'
            elif result == "FAIL":
                cell_class = ' class="fail"'
            elif result == "SKIPPED":
                cell_class = ' class="skipped"'
            transport_cells += f"<td{cell_class}>{escape(result)}</td>"

        tooltip = f' title="{escape(req.description)}"' if req.description else ""
        error_html = _format_transport_errors(req)
        test_html = _format_test_ids(req.test_ids)
        return (
            f"<tr>"
            f"<td{tooltip}>{escape(req_id)}</td>"
            f"<td>{escape(req.level)}</td>"
            f'<td class="{status_class}">{escape(req.status)}</td>'
            f"{transport_cells}"
            f"<td>{test_html}</td>"
            f"<td>{error_html}</td>"
            f"</tr>\n"
        )

    @staticmethod
    def _render_per_transport_summary(report: ComplianceReport) -> str:
        rows = ""
        for transport, t in report.per_transport.items():
            pct = (t.passed / t.total * 100) if t.total else 0
            rows += (
                "<tr>"
                f"<td>{escape(transport)}</td>"
                f"<td>{t.passed}</td>"
                f"<td>{t.failed}</td>"
                f"<td>{t.skipped}</td>"
                f"<td>{t.total}</td>"
                f"<td>"
                f'<div class="bar"><div class="bar-fill" style="width:{pct:.0f}%"></div></div>'
                f"</td>"
                "</tr>\n"
            )

        return (
            '<div class="section">\n'
            "<h2>Per-Transport Summary</h2>\n"
            "<table>\n"
            "<tr><th>Transport</th><th>Passed</th><th>Failed</th><th>Skipped</th><th>Total</th><th>Progress</th></tr>\n"
            f"{rows}"
            "</table>\n"
            "</div>\n"
        )

    @staticmethod
    def _render_failed_tests(report: ComplianceReport) -> str:
        failed = {
            req_id: req
            for req_id, req in report.per_requirement.items()
            if req.status == "FAIL"
        }
        if not failed:
            return (
                '<div class="section">\n'
                "<h2>Failed Tests</h2>\n"
                "<p>No failures.</p>\n"
                "</div>\n"
            )

        items = ""
        for req_id, req in failed.items():
            error_html = _format_transport_errors(req)
            if not error_html:
                error_html = "no error details"
            items += (
                f"<li><strong>{escape(req_id)}</strong> "
                f"[{escape(req.level)}]: {error_html}</li>\n"
            )

        return (
            '<div class="section">\n'
            "<h2>Failed Tests</h2>\n"
            f"<ul>\n{items}</ul>\n"
            "</div>\n"
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _format_compliance(value: float) -> str:
    return f"{value:.1f}%"


def _format_test_ids(test_ids: list[str]) -> str:
    """Format test IDs as a compact list showing class::method."""
    if not test_ids:
        return ""
    items = []
    for tid in test_ids:
        # Show only the Class::method part for brevity, full path as tooltip
        parts = tid.split("::")
        short = "::".join(parts[1:]) if len(parts) > 1 else tid
        items.append(
            f'<span class="test-id" title="{escape(tid)}">{escape(short)}</span>'
        )
    return "<br>".join(items)


def _format_transport_errors(req: RequirementResult) -> str:
    """Format errors as a bullet list grouped by transport."""
    if req.transport_errors:
        items = ""
        for transport, errs in req.transport_errors.items():
            for err in errs:
                items += f"<li><strong>{escape(transport)}</strong>: {escape(err)}</li>"
        return f"<ul class=\"error-list\">{items}</ul>"
    if req.errors:
        items = "".join(f"<li>{escape(e)}</li>" for e in req.errors)
        return f"<ul class=\"error-list\">{items}</ul>"
    return ""


# ------------------------------------------------------------------
# Inline CSS
# ------------------------------------------------------------------

_CSS = """
body { font-family: sans-serif; margin: 2em; color: #222; }
h1, h2 { margin-top: 1.5em; }
.section { margin-bottom: 2em; }
.overall { font-size: 2.5em; font-weight: bold; margin: 0.3em 0; }
table { border-collapse: collapse; width: 100%; margin-top: 0.5em; }
th, td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; }
th { background: #f5f5f5; }
.pass { background: #d4edda; color: #155724; }
.fail { background: #f8d7da; color: #721c24; }
.skipped { background: #e2e3e5; color: #383d41; }
.bar { background: #e9ecef; border-radius: 4px; height: 18px; width: 100%; }
.bar-fill { background: #28a745; height: 100%; border-radius: 4px; }
td[title] { cursor: help; text-decoration: underline dotted; }
.error-list { margin: 0; padding-left: 1.2em; list-style: disc; }
.error-list li { margin: 2px 0; }
.test-id { font-family: monospace; font-size: 0.85em; cursor: help; }
.agent-card { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 1em; overflow-x: auto; font-size: 0.85em; }
details summary { cursor: pointer; }
"""
