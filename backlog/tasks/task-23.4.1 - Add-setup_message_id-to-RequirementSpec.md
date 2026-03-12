---
id: TASK-23.4.1
title: Add setup_message_id to RequirementSpec
status: To Do
assignee: []
created_date: '2026-03-12 15:15'
labels:
  - tck
milestone: TCK Scenario System
dependencies: []
references:
  - tck/requirements/base.py
  - tck/requirements/core_operations.py
parent_task_id: TASK-23.4
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add optional `setup_message_id: str | None = None` field to the `RequirementSpec` dataclass in `tck/requirements/base.py`. Set it on all multi-operation requirements in `tck/requirements/core_operations.py` (CORE-SEND-002, CORE-CANCEL-002, CORE-GET-001, etc.) to match the prefixes used in the Gherkin scenarios.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 RequirementSpec has setup_message_id field
- [ ] #2 All multi-operation requirements have setup_message_id set
- [ ] #3 make lint and make unit-test pass
<!-- AC:END -->
