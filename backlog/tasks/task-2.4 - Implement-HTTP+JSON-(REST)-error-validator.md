---
id: task-2.4
title: Implement HTTP+JSON (REST) error validator
status: To Do
assignee: []
created_date: '2026-01-28 09:08'
labels:
  - phase-2
  - validation
  - rest
  - errors
dependencies: []
parent_task_id: task-2
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
- [ ] #1 tck/validators/rest/error_validator.py exists
- [ ] #2 HTTP_JSON_ERROR_STATUS dict contains all status mappings from PRD Section 8.2
- [ ] #3 ProblemDetails dataclass implements RFC 7807 structure
- [ ] #4 ErrorValidationResult has valid, expected_status, actual_status, problem_details fields
- [ ] #5 validate_http_json_error() validates HTTP status codes correctly
- [ ] #6 Problem Details are parsed when Content-Type is application/problem+json
<!-- AC:END -->
