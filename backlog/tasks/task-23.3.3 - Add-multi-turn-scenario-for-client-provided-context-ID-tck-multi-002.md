---
id: TASK-23.3.3
title: Add multi-turn scenario for client-provided context ID (tck-multi-002)
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
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a Gherkin scenario for `tck-multi-002` prefix to `scenarios/core_operations.feature`. This covers CORE-MULTI-002 (MAY) — the SDK handles preserving client-provided contextId, so the executor just needs to complete the task with a message.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Scenario with prefix tck-multi-002 added to core_operations.feature
- [ ] #2 Generated SUT handles tck-multi-002 prefix
- [ ] #3 CORE-MULTI-002 test passes
<!-- AC:END -->
