---
id: TASK-2.3
title: Implement JSON-RPC error validator
status: Done
assignee: []
created_date: '2026-01-28 09:08'
updated_date: '2026-02-24 12:44'
labels:
  - phase-2
  - validation
  - jsonrpc
  - errors
dependencies: []
parent_task_id: TASK-2
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement validation for JSON-RPC error responses according to the error code mappings in Section 9 of the A2A specification.

**Reference**: PRD Section 5.2.3 (Transport-Specific Validators), A2A Spec Section 9

**Location**: `tck/validators/jsonrpc/error_validator.py`

**Constants to define** (JSONRPC_ERROR_CODES):
- TaskNotFoundError: -32001
- TaskNotCancelableError: -32002
- PushNotificationNotSupportedError: -32003
- UnsupportedOperationError: -32004
- ContentTypeNotSupportedError: -32005
- InvalidAgentResponseError: -32006
- InvalidRequestError: -32600
- MethodNotFoundError: -32601
- InvalidParamsError: -32602
- InternalError: -32603
- VersionNotSupportedError: -32009

**Classes to implement**:

1. `ErrorValidationResult(dataclass)`:
   - valid: bool
   - expected_code: int
   - actual_code: int
   - message: str

2. `validate_jsonrpc_error(response: dict, expected_error: str) -> ErrorValidationResult`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tck/validators/jsonrpc/error_validator.py exists
- [x] #2 JSONRPC_ERROR_CODES dict contains all error codes from PRD Section 8.2
- [x] #3 ErrorValidationResult dataclass has valid, expected_code, actual_code, message fields
- [x] #4 validate_jsonrpc_error() returns valid=True when error code matches
- [x] #5 validate_jsonrpc_error() returns valid=False with details when error code mismatches
- [x] #6 Function handles missing 'error' field gracefully
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Implementation Summary

Implemented `tck/validators/jsonrpc/error_validator.py` with:

1. **JSONRPC_ERROR_CODES dict** containing all error codes:
   - A2A-specific: TaskNotFoundError (-32001), TaskNotCancelableError (-32002), etc.
   - Standard JSON-RPC: InvalidRequestError (-32600), MethodNotFoundError (-32601), etc.

2. **ErrorValidationResult dataclass** with fields:
   - `valid: bool`
   - `expected_code: int`
   - `actual_code: int | None`
   - `message: str`

3. **validate_jsonrpc_error()** function that:
   - Returns valid=True when error code matches
   - Returns valid=False with details when mismatch
   - Handles missing 'error' field gracefully
   - Handles malformed error objects

4. **Helper functions**: get_error_name(), get_error_code()

5. **Tests**: 28 tests covering all acceptance criteria
<!-- SECTION:NOTES:END -->
