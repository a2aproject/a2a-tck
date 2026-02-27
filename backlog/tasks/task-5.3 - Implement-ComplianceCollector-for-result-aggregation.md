---
id: TASK-5.3
title: Implement ComplianceCollector for result aggregation
status: Done
assignee: []
created_date: '2026-01-28 09:11'
updated_date: '2026-02-27 12:02'
labels:
  - phase-5
  - testing
  - reporting
dependencies: []
parent_task_id: TASK-5
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the compliance collector that aggregates test results during test execution.

**Reference**: PRD Section 5.5.1 (Compliance Report Structure)

**Location**: `tck/reporting/collector.py`

**Classes to implement**:

1. `TestResult(dataclass)`:
   - requirement_id: str
   - transport: str
   - passed: bool
   - errors: list[str]
   - level: Literal["MUST", "SHOULD", "MAY"]

2. `ComplianceCollector`:
   - `record(requirement_id, transport, passed, errors, level="MUST")`: Record single test result
   - `get_results() -> list[TestResult]`: Get all recorded results
   - `get_per_requirement() -> dict[str, dict[str, str]]`: Group by requirement
   - `get_per_transport() -> dict[str, dict[str, int]]`: Group by transport
   - `reset()`: Clear all results

This collector will be used by both tests and the reporting layer.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tck/reporting/collector.py exists
- [x] #2 TestResult dataclass has all required fields
- [x] #3 ComplianceCollector.record() stores test results
- [x] #4 get_results() returns all recorded results
- [x] #5 get_per_requirement() groups results by requirement ID
- [x] #6 get_per_transport() groups results by transport
- [x] #7 reset() clears all stored results
<!-- AC:END -->
