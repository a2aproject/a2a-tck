---
id: TASK-7.5
title: Integrate reporting with pytest hooks
status: Done
assignee: []
created_date: '2026-01-28 09:13'
updated_date: '2026-03-04 09:44'
labels:
  - phase-7
  - reporting
  - pytest
dependencies:
  - task-7.2
  - task-7.3
  - task-7.4
parent_task_id: TASK-7
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Integrate the reporting system with pytest hooks for automatic report generation.

**Reference**: PRD Section 6 Task 7.5, Section 7.2

**Location**: `tests/compatibility/conftest.py` (add hooks)

**Hooks to implement**:

1. `pytest_runtest_makereport`:
   - Capture test results as they complete
   - Extract requirement ID and transport from test name
   - Record to ComplianceCollector

2. `pytest_sessionfinish`:
   - Aggregate results using ComplianceAggregator
   - Generate reports if --compliance-report specified
   - Print console summary

3. `pytest_configure`:
   - Initialize ComplianceCollector
   - Set up report output paths

**Integration with CLI**:
- Honor --compliance-report path for output
- Generate all formats (JSON, HTML) when report requested
- Always show console summary at end
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 pytest_runtest_makereport hook captures results
- [ ] #2 pytest_sessionfinish generates reports
- [ ] #3 Reports are generated when --compliance-report is specified
- [ ] #4 Console summary is printed after test run
- [ ] #5 Requirement ID and transport are extracted from test names
- [ ] #6 Reports directory is created if it doesn't exist
<!-- AC:END -->
