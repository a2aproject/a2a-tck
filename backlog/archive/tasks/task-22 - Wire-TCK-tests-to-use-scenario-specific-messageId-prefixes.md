---
id: TASK-22
title: Wire TCK tests to use scenario-specific messageId prefixes
status: To Do
assignee: []
created_date: '2026-03-12 15:13'
labels:
  - phase-4
  - tck
milestone: TCK Scenario System
dependencies:
  - TASK-21
references:
  - tck/requirements/base.py
  - tck/requirements/core_operations.py
  - tests/compatibility/_task_helpers.py
  - tests/compatibility/core_operations/test_task_lifecycle.py
  - docs/SUT_REQUIREMENTS.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Update TCK code to use deterministic messageId prefixes matching the Gherkin scenarios:\n\n1. Add `setup_message_id: str | None = None` field to `RequirementSpec` in `tck/requirements/base.py`\n2. Set `setup_message_id` on multi-operation requirements in `tck/requirements/core_operations.py` (CORE-SEND-002, CORE-CANCEL-002, CORE-GET-001, etc.)\n3. Update `create_task()` in `tests/compatibility/_task_helpers.py` to accept optional `message_id` parameter\n4. Update multi-operation tests in `test_task_lifecycle.py` to pass `tck_id(req.setup_message_id)` to `create_task()`\n5. Update `docs/SUT_REQUIREMENTS.md` to reference `scenarios/*.feature` as the source of truth
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 RequirementSpec has setup_message_id field
- [ ] #2 All multi-operation requirements have setup_message_id set
- [ ] #3 create_task() accepts optional message_id parameter
- [ ] #4 Multi-operation tests use scenario-specific messageIds instead of generic ones
- [ ] #5 SUT_REQUIREMENTS.md references scenarios/*.feature
- [ ] #6 make lint and make unit-test pass
<!-- AC:END -->
