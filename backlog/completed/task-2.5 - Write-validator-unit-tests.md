---
id: TASK-2.5
title: Write validator unit tests
status: Done
assignee: []
created_date: '2026-01-28 09:08'
updated_date: '2026-02-25 08:23'
labels:
  - phase-2
  - validation
  - testing
dependencies:
  - task-2.1
  - task-2.2
  - task-2.3
  - task-2.4
parent_task_id: TASK-2
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Write comprehensive unit tests for all validators to ensure they correctly identify valid and invalid responses.

**Reference**: PRD Section 6 Task 2.5

**Location**: `tests/unit/test_validators.py` (or split by validator type)

**Test coverage**:

1. **JSONSchemaValidator tests**:
   - Valid Task object passes validation
   - Invalid Task (missing required field) fails with clear error
   - Valid Message with all part types passes
   - Invalid Part (wrong oneof) fails
   - Schema reference resolution works correctly

2. **ProtoSchemaValidator tests**:
   - Valid proto message passes
   - Wrong type fails with type error message
   - Missing required field fails
   - Nested message validation works

3. **JSON-RPC error validator tests**:
   - Each error type maps to correct code
   - Mismatched code returns valid=False
   - Missing error field handled gracefully

4. **REST error validator tests**:
   - Each error type maps to correct HTTP status
   - Problem Details parsed correctly
   - Non-problem+json response handled

**Note**: These unit tests add value because validators are complex logic with many edge cases.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Unit tests exist for JSONSchemaValidator
- [x] #2 Unit tests exist for ProtoSchemaValidator
- [x] #3 Unit tests exist for JSON-RPC error validator
- [x] #4 Unit tests exist for REST error validator
- [x] #5 Tests cover both valid and invalid cases
- [x] #6 Tests use mock/fixture data, not live servers
- [x] #7 All tests pass with pytest tests/unit/
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
All validator unit tests already exist in `tests/validators/` and pass (105 tests in 0.13s). Coverage includes:\n\n- **JSONSchemaValidator** (19 tests): valid/invalid responses, error collection, JSON path formatting, schema ref formats, $ref resolution\n- **ProtoSchemaValidator** (14 tests): type checks, required fields, nested messages, repeated fields, error messages, AgentCard validation\n- **JSON-RPC error validator** (20 tests): all 11 error codes, edge cases (missing fields, wrong types), helper functions\n- **HTTP+JSON error validator** (33 tests): ProblemDetails parsing, all error types, case-insensitive headers, helper functions\n\nTests are organized in `tests/validators/` (split by validator type) rather than the originally suggested `tests/unit/test_validators.py`. All tests use mock/fixture data with no live server dependencies.
<!-- SECTION:FINAL_SUMMARY:END -->
