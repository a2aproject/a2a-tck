---
id: TASK-23.3.4
title: Add multi-turn scenario for task ID generation (tck-multi-003)
status: To Do
assignee: []
created_date: '2026-03-13 13:23'
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
Add a Gherkin scenario for `tck-multi-003` prefix to `scenarios/core_operations.feature`. This covers CORE-MULTI-003 (MUST) — the SDK generates a unique taskId, so the executor just needs to complete the task with a message.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Scenario with prefix tck-multi-003 added to core_operations.feature
- [ ] #2 Generated SUT handles tck-multi-003 prefix
- [ ] #3 CORE-MULTI-003 test passes
<!-- AC:END -->
