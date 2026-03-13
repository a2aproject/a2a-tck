---
id: task-7.2
title: Implement JSON compliance report formatter
status: To Do
assignee: []
created_date: '2026-01-28 09:13'
labels:
  - phase-7
  - reporting
  - json
dependencies:
  - task-7.1
parent_task_id: task-7
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the JSON formatter that outputs machine-readable compliance reports.

**Reference**: PRD Section 6 Task 7.2, Section 5.5.1

**Location**: `tck/reporting/formatters.py` (or `tck/reporting/json_formatter.py`)

**Function/Class**: `JSONFormatter` or `format_json(report: ComplianceReport) -> str`

**Output structure** (from PRD):
```json
{
  "summary": {
    "timestamp": "2025-01-27T10:30:00Z",
    "sut_url": "http://localhost:9999",
    "spec_version": "1.0",
    "overall_compliance": "98.5%",
    "must_compliance": "100%",
    "should_compliance": "95%"
  },
  "per_requirement": {
    "REQ-3.1": {"grpc": "PASS", "jsonrpc": "PASS", "rest": "FAIL"}
  },
  "per_transport": {
    "grpc": {"passed": 100, "failed": 0, "total": 100}
  },
  "corner_cases": {...}
}
```

**Output file**: `reports/compliance.json`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 JSON formatter function/class exists
- [ ] #2 Output matches PRD structure exactly
- [ ] #3 JSON is valid and parseable
- [ ] #4 Timestamp is ISO 8601 format
- [ ] #5 Compliance percentages are formatted as strings with %
- [ ] #6 File is written to reports/compliance.json
<!-- AC:END -->
