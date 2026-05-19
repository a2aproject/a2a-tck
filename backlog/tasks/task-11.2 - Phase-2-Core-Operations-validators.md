---
id: TASK-11.2
title: 'Phase 2: Core Operations validators'
status: To Do
assignee: []
created_date: '2026-03-11 16:40'
labels:
  - validators
  - core-operations
dependencies:
  - TASK-11.1
parent_task_id: TASK-11
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Attach payload validators to requirements in `tck/requirements/core_operations.py` (~25 requirements need validators, ~30 are error-only/skip).

## Requirements to add validators to

**SendMessage:**
- CORE-SEND-001: `validate_response_is_task_or_message()`

**GetTask:**
- CORE-GET-001: `validate_response_is_task()`, `validate_task_has_required_fields()`

**ListTasks:**
- CORE-LIST-001: `validate_response_is_list()` (tasks array present)
- CORE-LIST-003: `validate_list_sorted_by_timestamp_desc()`
- CORE-LIST-004: `validate_next_page_token_empty_on_final_page()`
- CORE-LIST-005: `validate_field_absent("artifacts")`

**CancelTask:**
- CORE-CANCEL-001: `validate_response_is_task()`, `validate_task_state(["canceled"])`

**Blocking:**
- CORE-BLOCK-001: `validate_task_state(terminal + interrupted states)`
- CORE-BLOCK-002: `validate_response_is_task_or_message()`

**Multi-Turn:**
- CORE-MULTI-001a: already has validator ✓
- CORE-MULTI-003: `validate_response_contains_field("id")` (taskId in Task)
- CORE-MULTI-005: `validate_response_contains_field("contextId")`

**Skip (error-only, already covered by error validators):**
- CORE-SEND-002, SEND-003, GET-002, CANCEL-002, CANCEL-003, MULTI-002a, MULTI-004, MULTI-006, CAP-001/002/003/004, ERR-001/002

## Key files
- `tck/requirements/core_operations.py`
- `tck/validators/payload.py`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All non-error core operation requirements reviewed and validators attached where applicable
- [ ] #2 Error-only requirements documented as not needing payload validators
- [ ] #3 make lint and make unit-test pass
<!-- AC:END -->
