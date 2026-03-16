---
id: TASK-23.1.1
title: Create core_operations.feature
status: Done
assignee: []
created_date: '2026-03-12 15:15'
updated_date: '2026-03-16 09:39'
labels:
  - gherkin
  - scenarios
milestone: TCK Scenario System
dependencies: []
references:
  - scenarios/core_operations.feature
  - tck/requirements/core_operations.py
parent_task_id: TASK-23.1
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create `scenarios/core_operations.feature` with Gherkin scenarios for all core TCK requirements. Covers: basic completion (tck-send-001), terminal rejection setup (tck-setup-send-002), unsupported content type (tck-send-003), artifacts (text/file/data parts), message response, input_required state, GetTask/CancelTask setup tasks, blocking/non-blocking modes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 scenarios/core_operations.feature exists with valid Gherkin syntax
- [x] #2 Every multi-operation TCK requirement has a corresponding setup scenario
- [x] #3 Step vocabulary covers: complete task, reject with error, add artifact (text/file/data), return message, set task state
- [x] #4 Scenarios use messageId prefix convention matching tck_id() patterns
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The `scenarios/core_operations.feature` file was already complete with 12 valid Gherkin scenarios covering all core TCK requirements. Fixed a minor section comment (CancelTask Section 3.1.4 → 3.1.5). All acceptance criteria verified:

1. File exists and parses with valid Gherkin syntax (12 scenarios)
2. Every multi-operation requirement (CORE-GET-001, CORE-CANCEL-001/002, CORE-SEND-002, CORE-MULTI-005/006) has setup scenarios via `tck-task-helper` and `tck-input-required` prefixes
3. Step vocabulary covers: complete task, reject with error, add artifact (text/file/data), return message, set task state
4. All prefixes follow the `tck-{suffix}` convention matching `tck_id()` patterns
<!-- SECTION:FINAL_SUMMARY:END -->
