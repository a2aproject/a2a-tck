---
id: task-2.3
title: Implement JSON-RPC error validator
status: To Do
assignee: []
created_date: '2026-01-28 09:08'
labels:
  - phase-2
  - validation
  - jsonrpc
  - errors
dependencies: []
parent_task_id: task-2
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
- [ ] #1 tck/validators/jsonrpc/error_validator.py exists
- [ ] #2 JSONRPC_ERROR_CODES dict contains all error codes from PRD Section 8.2
- [ ] #3 ErrorValidationResult dataclass has valid, expected_code, actual_code, message fields
- [ ] #4 validate_jsonrpc_error() returns valid=True when error code matches
- [ ] #5 validate_jsonrpc_error() returns valid=False with details when error code mismatches
- [ ] #6 Function handles missing 'error' field gracefully
<!-- AC:END -->
