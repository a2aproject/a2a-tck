---
id: TASK-6.1
title: Implement JSON-RPC error code tests
status: To Do
assignee: []
created_date: '2026-01-28 09:12'
updated_date: '2026-02-27 13:36'
labels:
  - phase-6
  - testing
  - jsonrpc
  - errors
dependencies: []
parent_task_id: TASK-6
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement tests that validate JSON-RPC error code mappings per A2A Specification Section 9.

**Reference**: PRD Section 6 Task 6.1, PRD Section 5.4.2

**Location**: `tests/compatibility/jsonrpc/test_error_codes.py`

**Test class**: `TestJsonRpcErrorCodes`

**Tests to implement**:

1. `test_task_not_found_error`: TaskNotFoundError → code -32001
2. `test_task_not_cancelable_error`: TaskNotCancelableError → code -32002
3. `test_push_notification_not_supported_error`: → code -32003
4. `test_unsupported_operation_error`: → code -32004
5. `test_content_type_not_supported_error`: → code -32005
6. `test_invalid_agent_response_error`: → code -32006
7. `test_version_not_supported_error`: → code -32009
8. `test_error_code_mapping`: Parametrized test of all mappings

**Test approach**:
- Trigger each error condition
- Validate response has correct error code
- Validate error message is present
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tests/jsonrpc/test_error_codes.py exists
- [ ] #2 TaskNotFoundError test validates -32001 code
- [ ] #3 All error types from PRD Section 8.2 are tested
- [ ] #4 Tests trigger actual error conditions on SUT
- [ ] #5 Tests validate both error code and message presence
- [ ] #6 Parametrized test covers all error mappings
<!-- AC:END -->
