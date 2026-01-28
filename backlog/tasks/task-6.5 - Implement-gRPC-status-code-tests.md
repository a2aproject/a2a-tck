---
id: task-6.5
title: Implement gRPC status code tests
status: To Do
assignee: []
created_date: '2026-01-28 09:12'
labels:
  - phase-6
  - testing
  - grpc
  - status-codes
dependencies: []
parent_task_id: task-6
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement tests that validate gRPC status code mappings per A2A Specification Section 10.

**Reference**: PRD Section 6 Task 6.5, A2A Spec Section 10

**Location**: `tests/grpc/test_status_codes.py`

**Test class**: `TestGrpcStatusCodes`

**Tests to implement**:

1. `test_task_not_found_status`:
   - GetTask for nonexistent task returns NOT_FOUND

2. `test_invalid_argument_status`:
   - Invalid request returns INVALID_ARGUMENT

3. `test_failed_precondition_status`:
   - TaskNotCancelable returns FAILED_PRECONDITION

4. `test_unimplemented_status`:
   - Unsupported operation returns UNIMPLEMENTED

5. `test_internal_status`:
   - Server errors return INTERNAL

6. `test_status_code_details`:
   - Error details contain A2A error type

**gRPC status codes to test**:
- NOT_FOUND, INVALID_ARGUMENT, FAILED_PRECONDITION
- UNIMPLEMENTED, INTERNAL, UNAUTHENTICATED
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tests/grpc/test_status_codes.py exists
- [ ] #2 NOT_FOUND status is tested for TaskNotFoundError
- [ ] #3 INVALID_ARGUMENT is tested for invalid requests
- [ ] #4 FAILED_PRECONDITION is tested for TaskNotCancelable
- [ ] #5 UNIMPLEMENTED is tested for unsupported operations
- [ ] #6 Error details contain A2A error type information
<!-- AC:END -->
