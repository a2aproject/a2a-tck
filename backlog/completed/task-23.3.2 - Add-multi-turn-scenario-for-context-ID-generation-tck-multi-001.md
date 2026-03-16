---
id: TASK-23.3.2
title: Add multi-turn scenario for context ID generation (tck-multi-001)
status: Done
assignee: []
created_date: '2026-03-13 13:23'
updated_date: '2026-03-16 10:32'
labels:
  - scenario
  - multi-turn
milestone: TCK Scenario System
dependencies: []
references:
  - tck/requirements/core_operations.py
  - scenarios/core_operations.feature
parent_task_id: TASK-23.3
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a Gherkin scenario for `tck-multi-001` prefix to `scenarios/core_operations.feature`. This covers CORE-MULTI-001 (MAY) and CORE-MULTI-001a (MUST) — the SDK handles contextId generation and inclusion in the response, so the executor just needs to complete the task with a message.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Scenario with prefix tck-multi-001 added to core_operations.feature
- [x] #2 Generated SUT handles tck-multi-001 prefix
- [x] #3 CORE-MULTI-001 and CORE-MULTI-001a tests pass
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added scenario for `tck-multi-001` prefix to `core_operations.feature`. The executor completes the task with a message; contextId generation is handled by the SDK. CORE-MULTI-001 (MAY) and CORE-MULTI-001a (MUST) pass on all three transports.
<!-- SECTION:FINAL_SUMMARY:END -->
