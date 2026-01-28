---
id: task-7.4
title: Implement console summary output
status: To Do
assignee: []
created_date: '2026-01-28 09:13'
labels:
  - phase-7
  - reporting
  - console
dependencies:
  - task-7.1
parent_task_id: task-7
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the console formatter that outputs a quick summary to the terminal.

**Reference**: PRD Section 6 Task 7.4

**Location**: `tck/reporting/formatters.py` (or `tck/reporting/console_formatter.py`)

**Function/Class**: `ConsoleFormatter` or `format_console(report: ComplianceReport) -> str`

**Output format**:
```
═══════════════════════════════════════════════════════
           A2A TCK Compliance Report
═══════════════════════════════════════════════════════

SUT: http://localhost:9999
Spec Version: 1.0
Timestamp: 2025-01-27 10:30:00

OVERALL COMPLIANCE: 98.5%

┌─────────────┬────────┬────────┬───────┐
│ Level       │ Passed │ Failed │ Total │
├─────────────┼────────┼────────┼───────┤
│ MUST        │    100 │      0 │   100 │
│ SHOULD      │     45 │      5 │    50 │
│ MAY         │     20 │      0 │    20 │
└─────────────┴────────┴────────┴───────┘

BY TRANSPORT:
  gRPC:      100/100 ✓
  JSON-RPC:   98/100 ⚠
  REST:       95/100 ⚠

FAILED REQUIREMENTS:
  ✗ REQ-9.3 (JSON-RPC): Error code mismatch
  ✗ REQ-11.2 (REST): Missing Problem Details
═══════════════════════════════════════════════════════
```

**Features**:
- Use ANSI colors if terminal supports it
- Show only essential information
- List failed tests with brief error
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Console formatter function/class exists
- [ ] #2 Output shows overall compliance prominently
- [ ] #3 Table shows pass/fail counts by level
- [ ] #4 Per-transport summary is included
- [ ] #5 Failed requirements are listed with brief error
- [ ] #6 ANSI colors are used when terminal supports it
- [ ] #7 Output is concise (fits on one screen for typical results)
<!-- AC:END -->
