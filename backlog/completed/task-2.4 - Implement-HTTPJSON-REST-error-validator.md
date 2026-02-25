---
id: TASK-2.4
title: Implement HTTP+JSON (REST) error validator
status: Done
assignee: []
created_date: '2026-01-28 09:08'
updated_date: '2026-02-24 15:28'
labels:
  - phase-2
  - validation
  - rest
  - errors
dependencies: []
parent_task_id: TASK-2
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement validation for HTTP+JSON error responses according to Section 11 of the A2A specification, including RFC 7807 Problem Details support.

**Reference**: PRD Section 5.2.3 (Transport-Specific Validators), A2A Spec Section 11

**Location**: `tck/validators/rest/error_validator.py`

**Constants to define** (HTTP_JSON_ERROR_STATUS):
- TaskNotFoundError: 404
- TaskNotCancelableError: 400
- UnsupportedOperationError: 400
- ContentTypeNotSupportedError: 415
- VersionNotSupportedError: 400
- InvalidRequestError: 400
- InternalError: 500

**Classes to implement**:

1. `ProblemDetails(dataclass)` - RFC 7807 structure:
   - type: str
   - title: str
   - status: int
   - detail: str = ""
   - instance: str = ""

2. `ErrorValidationResult(dataclass)`:
   - valid: bool
   - expected_status: int
   - actual_status: int
   - problem_details: ProblemDetails | None

3. `validate_http_json_error(response, expected_error: str) -> ErrorValidationResult`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tck/validators/rest/error_validator.py exists
- [x] #2 HTTP_JSON_ERROR_STATUS dict contains all status mappings from PRD Section 8.2
- [x] #3 ProblemDetails dataclass implements RFC 7807 structure
- [x] #4 ErrorValidationResult has valid, expected_status, actual_status, problem_details fields
- [x] #5 validate_http_json_error() validates HTTP status codes correctly
- [x] #6 Problem Details are parsed when Content-Type is application/problem+json
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Implementation Summary

Implemented `tck/validators/rest/error_validator.py` with:

1. **HTTP_JSON_ERROR_STATUS dict** with status mappings:
   - TaskNotFoundError: 404
   - ContentTypeNotSupportedError: 415
   - InternalError: 500
   - Various 400 errors: TaskNotCancelableError, InvalidRequestError, etc.

2. **ProblemDetails dataclass** (RFC 7807):
   - type, title, status (required)
   - detail, instance (optional)
   - from_dict() class method

3. **ErrorValidationResult dataclass**:
   - valid, expected_status, actual_status, problem_details, message

4. **validate_http_json_error()** function:
   - Validates HTTP status codes
   - Parses RFC 7807 Problem Details when Content-Type is application/problem+json
   - Supports both dict and HTTP response objects

5. **Tests**: 33 tests covering all acceptance criteria
<!-- SECTION:NOTES:END -->
