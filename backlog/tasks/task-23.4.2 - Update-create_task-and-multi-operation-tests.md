---
id: TASK-23.4.2
title: Update create_task() and multi-operation tests
status: To Do
assignee: []
created_date: '2026-03-12 15:15'
labels:
  - tck
milestone: TCK Scenario System
dependencies: []
references:
  - tests/compatibility/_task_helpers.py
  - tests/compatibility/core_operations/test_task_lifecycle.py
  - docs/SUT_REQUIREMENTS.md
parent_task_id: TASK-23.4
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
1. Update `create_task()` in `tests/compatibility/_task_helpers.py` to accept optional `message_id` parameter.\n2. Update multi-operation tests in `test_task_lifecycle.py` to pass `tck_id(req.setup_message_id)` to `create_task()` instead of using generic messages.\n3. Update `docs/SUT_REQUIREMENTS.md` to reference `scenarios/*.feature` as the source of truth for SUT behavior.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 create_task() accepts optional message_id parameter
- [ ] #2 Multi-operation tests use scenario-specific messageIds
- [ ] #3 SUT_REQUIREMENTS.md references scenarios/*.feature
- [ ] #4 make lint and make unit-test pass
<!-- AC:END -->
