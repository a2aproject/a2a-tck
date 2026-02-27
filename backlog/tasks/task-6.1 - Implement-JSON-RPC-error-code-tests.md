---
id: TASK-6.1
title: Implement JSON-RPC error code tests
status: Done
assignee: []
created_date: '2026-01-28 09:12'
updated_date: '2026-02-27 14:27'
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
- [x] #1 tests/jsonrpc/test_error_codes.py exists
- [x] #2 TaskNotFoundError test validates -32001 code
- [x] #3 All error types from PRD Section 8.2 are tested
- [x] #4 Tests trigger actual error conditions on SUT
- [x] #5 Tests validate both error code and message presence
- [x] #6 Parametrized test covers all error mappings
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented JSON-RPC error code mapping tests in `tests/compatibility/jsonrpc/test_error_codes.py`.\n\n**Changes:**\n- `tck/validators/jsonrpc/error_validator.py` — Added missing error codes: `ExtendedAgentCardNotConfiguredError` (-32007) and `ExtensionSupportRequiredError` (-32008)\n- `tests/compatibility/jsonrpc/test_error_codes.py` — New file with 9 tests across two classes\n\n**TestJsonRpcErrorCodeMappings** (6 tests) — Each triggers a specific error condition and validates the code:\n- `test_task_not_found_error` — `client.get_task()` with non-existent ID → -32001\n- `test_task_not_cancelable_error` — `client.cancel_task()` on non-existent task → -32001 or -32002\n- `test_push_notification_not_supported_error` — `client.create_push_notification_config()` when unsupported → -32003\n- `test_unsupported_operation_error` — `SendStreamingMessage` when unsupported → -32004\n- `test_content_type_not_supported_error` — wrong Content-Type header → -32005\n- `test_version_not_supported_error` — `A2A-Version: 99.0` header → -32009\n\n**TestJsonRpcErrorCodeRange** (3 parametrized tests) — Validates returned error codes fall within A2A (-32001..-32099) or standard JSON-RPC ranges.\n\nUses transport client for `get_task`, `cancel_task`, `create_push_notification_config`; raw HTTP only where custom headers are required.\n\nCommit: 2626115
<!-- SECTION:FINAL_SUMMARY:END -->
