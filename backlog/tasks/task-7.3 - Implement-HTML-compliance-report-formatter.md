---
id: TASK-7.3
title: Implement HTML compliance report formatter
status: Done
assignee: []
created_date: '2026-01-28 09:13'
updated_date: '2026-03-03 11:31'
labels:
  - phase-7
  - reporting
  - html
dependencies:
  - task-7.1
parent_task_id: TASK-7
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the HTML formatter that outputs human-readable compliance reports.

**Reference**: PRD Section 6 Task 7.3

**Location**: `tck/reporting/formatters.py` (or `tck/reporting/html_formatter.py`)

**Function/Class**: `HTMLFormatter` or `format_html(report: ComplianceReport) -> str`

**Report sections**:

1. **Executive Summary**:
   - Overall compliance score (large, prominent)
   - MUST/SHOULD/MAY breakdowns
   - Timestamp and SUT URL

2. **Per-Requirement Table**:
   - Columns: Requirement ID, Title, gRPC, JSON-RPC, REST
   - Color coding: green (pass), red (fail), yellow (warning)
   - Sortable/filterable if practical

3. **Per-Transport Summary**:
   - Bar chart or progress bars
   - Pass/fail counts per transport

4. **Failed Tests Details**:
   - List of failed requirements with error messages
   - Links to spec sections

**Output file**: `reports/compliance.html`

**Styling**: Use inline CSS or minimal external CSS for portability.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 HTML formatter function/class exists
- [ ] #2 Report has executive summary section
- [ ] #3 Per-requirement table shows all results
- [ ] #4 Color coding indicates pass/fail/warning
- [ ] #5 Per-transport summary is included
- [ ] #6 Failed tests section shows error details
- [ ] #7 HTML is valid and renders correctly in browsers
- [ ] #8 File is written to reports/compliance.html
<!-- AC:END -->
