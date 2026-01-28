---
id: task-2.5
title: Write validator unit tests
status: To Do
assignee: []
created_date: '2026-01-28 09:08'
labels:
  - phase-2
  - validation
  - testing
dependencies:
  - task-2.1
  - task-2.2
  - task-2.3
  - task-2.4
parent_task_id: task-2
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
- [ ] #1 Unit tests exist for JSONSchemaValidator
- [ ] #2 Unit tests exist for ProtoSchemaValidator
- [ ] #3 Unit tests exist for JSON-RPC error validator
- [ ] #4 Unit tests exist for REST error validator
- [ ] #5 Tests cover both valid and invalid cases
- [ ] #6 Tests use mock/fixture data, not live servers
- [ ] #7 All tests pass with pytest tests/unit/
<!-- AC:END -->
