---
id: TASK-23.4
title: 'Phase 4: Wire TCK tests to scenario messageId prefixes'
status: To Do
assignee: []
created_date: '2026-03-12 15:14'
updated_date: '2026-03-12 15:19'
labels:
  - phase-4
  - tck
milestone: TCK Scenario System
dependencies: []
parent_task_id: TASK-23
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Update TCK code so multi-operation tests use deterministic messageId prefixes matching the Gherkin scenarios, eliminating flaky pytest.skip guards.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 RequirementSpec dataclass in base.py has setup_message_id: str | None = None
- [ ] #2 All multi-operation requirements (CORE-SEND-002, CORE-CANCEL-002, CORE-GET-001, etc.) have setup_message_id set
- [ ] #3 create_task() in _task_helpers.py accepts optional message_id parameter
- [ ] #4 Multi-operation tests in test_task_lifecycle.py use tck_id(req.setup_message_id)
- [ ] #5 docs/SUT_REQUIREMENTS.md references scenarios/*.feature as source of truth
- [ ] #6 make lint and make unit-test pass
<!-- AC:END -->
