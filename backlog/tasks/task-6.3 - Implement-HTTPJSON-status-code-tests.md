---
id: TASK-6.3
title: Implement HTTP+JSON status code tests
status: To Do
assignee: []
created_date: '2026-01-28 09:12'
updated_date: '2026-02-27 13:36'
labels:
  - phase-6
  - testing
  - http_json
dependencies: []
parent_task_id: TASK-6
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement tests that validate HTTP+JSON (REST) status code mappings per A2A Specification Section 11.

**Reference**: PRD Section 6 Task 6.3, PRD Section 5.4.2

**Location**: `tests/compatibility/http_json/test_http_status.py`

**Test class**: `TestHttpJsonStatus`

**Tests to implement**:

1. `test_task_not_found_returns_404`:
   - GET /tasks/{nonexistent} returns 404

2. `test_task_not_cancelable_returns_400`:
   - POST /tasks/{id}:cancel on non-cancelable returns 400

3. `test_unsupported_operation_returns_400`:
   - Unsupported operation returns 400

4. `test_content_type_not_supported_returns_415`:
   - Wrong Content-Type returns 415

5. `test_internal_error_returns_500`:
   - Server errors return 500

6. `test_success_returns_200_or_201`:
   - Successful operations return 2xx

**Test approach**:
- Trigger each error condition via REST client
- Validate HTTP status code matches expected
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tests/rest/test_http_status.py exists
- [ ] #2 404 status for TaskNotFoundError is tested
- [ ] #3 400 status for client errors is tested
- [ ] #4 415 status for ContentTypeNotSupportedError is tested
- [ ] #5 500 status for InternalError is tested
- [ ] #6 Success status codes are validated
<!-- AC:END -->
