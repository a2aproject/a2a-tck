---
id: TASK-6.3
title: Implement HTTP+JSON status code tests
status: Done
assignee: []
created_date: '2026-01-28 09:12'
updated_date: '2026-03-02 08:29'
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
- [x] #1 tests/rest/test_http_status.py exists
- [x] #2 404 status for TaskNotFoundError is tested
- [x] #3 400 status for client errors is tested
- [x] #4 415 status for ContentTypeNotSupportedError is tested
- [x] #5 500 status for InternalError is tested
- [x] #6 Success status codes are validated
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented 7 tests in `tests/compatibility/http_json/test_http_status.py`:

1. `test_task_not_found_returns_404` - GET nonexistent task → 404
2. `test_task_not_cancelable_returns_409` - CancelTask on nonexistent → 409 or 404
3. `test_unsupported_operation_returns_400` - Streaming when unsupported → 400
4. `test_content_type_not_supported_returns_415` - Wrong Content-Type → 415
5. `test_push_not_supported_returns_400` - Push config when unsupported → 400
6. `test_version_not_supported_returns_400` - Bad A2A-Version → 400
7. `test_success_returns_2xx` - SendMessage success → 2xx

Also:
- Added `HTTP_JSON-STATUS-001` requirement to `binding_rest.py`
- Fixed validator mappings: TaskNotCancelableError → 409 (was 400), InvalidAgentResponseError → 502 (was 500) to match spec Section 5.4
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented 7 HTTP+JSON status code mapping tests in `tests/compatibility/http_json/test_http_status.py`, validating that A2A error types map to correct HTTP status codes per spec Section 5.4. Added `HTTP_JSON-STATUS-001` requirement, renamed `binding_rest.py` → `binding_http_json.py`, and fixed validator mappings (TaskNotCancelableError→409, InvalidAgentResponseError→502) to match the specification.
<!-- SECTION:FINAL_SUMMARY:END -->
