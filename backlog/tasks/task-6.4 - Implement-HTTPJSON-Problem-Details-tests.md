---
id: TASK-6.4
title: Implement HTTP+JSON Problem Details tests
status: To Do
assignee: []
created_date: '2026-01-28 09:12'
updated_date: '2026-02-24 15:37'
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
Implement tests for RFC 7807 Problem Details format in HTTP+JSON error responses.

**Reference**: PRD Section 6 Task 6.4, PRD Section 5.2.3, RFC 7807

**Location**: `tests/rest/test_problem_details.py`

**Test class**: `TestProblemDetails`

**Tests to implement**:

1. `test_error_response_content_type`:
   - Error responses have Content-Type: application/problem+json

2. `test_problem_details_required_fields`:
   - Response contains: type, title, status
   - Fields have correct values

3. `test_problem_details_optional_fields`:
   - Response may contain: detail, instance
   - Fields are valid when present

4. `test_problem_details_type_matches_error`:
   - type field matches A2A error type (e.g., "TaskNotFoundError")

5. `test_problem_details_status_matches_http`:
   - status field matches HTTP status code

**RFC 7807 structure**:
```json
{
  "type": "TaskNotFoundError",
  "title": "Task not found",
  "status": 404,
  "detail": "Task with id 'xyz' does not exist",
  "instance": "/tasks/xyz"
}
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tests/rest/test_problem_details.py exists
- [ ] #2 Content-Type application/problem+json is validated
- [ ] #3 Required fields (type, title, status) are validated
- [ ] #4 Optional fields (detail, instance) are tested when present
- [ ] #5 type field matches A2A error type
- [ ] #6 status field matches HTTP status code
<!-- AC:END -->
