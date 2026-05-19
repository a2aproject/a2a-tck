---
id: TASK-23.3.5
title: 'Fix CORE-CANCEL-001: add cancelable task scenario and update test'
status: Done
assignee: []
created_date: '2026-03-13 13:36'
updated_date: '2026-03-13 13:49'
labels:
  - scenario
  - cancel
  - test-fix
milestone: TCK Scenario System
dependencies: []
references:
  - scenarios/core_operations.feature
  - tests/compatibility/core_operations/test_task_lifecycle.py
  - tests/compatibility/_task_helpers.py
parent_task_id: TASK-23.3
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
CORE-CANCEL-001 fails on all transports because `create_task()` uses `tck-task-helper` which immediately completes the task. When CancelTask is called, the SDK correctly returns TaskNotCancelableError since the task is already terminal.

Fix requires:
1. Add a `tck-cancel-001` scenario to `core_operations.feature` that puts the task in `input_required` state (non-terminal, cancelable)
2. Update `test_cancel_task_returns_updated_state` to create a task with the `tck-cancel-001` prefix instead of using `create_task()`
3. Regenerate the Java SUT and verify the test passes
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Scenario with prefix tck-cancel-001 added to core_operations.feature that leaves task in input_required state
- [ ] #2 test_cancel_task_returns_updated_state uses tck-cancel-001 prefix to create a cancelable task
- [ ] #3 CORE-CANCEL-001 passes on all three transports
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added `tck-cancel-001` scenario to `scenarios/core_operations.feature` with `input_required` state (non-terminal, cancelable). Updated `test_cancel_task_returns_updated_state` to use a dedicated `_create_cancelable_task()` helper instead of `create_task()` which immediately completes. Regenerated SUT. CORE-CANCEL-001 now passes on all 3 transports. Committed as e8f8434.
<!-- SECTION:FINAL_SUMMARY:END -->
