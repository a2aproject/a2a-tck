---
id: TASK-2.2
title: Implement ProtoSchemaValidator class
status: In Progress
assignee: []
created_date: '2026-01-28 09:08'
updated_date: '2026-02-23 14:14'
labels:
  - phase-2
  - validation
  - proto
dependencies:
  - task-1.5
parent_task_id: TASK-2
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the Proto Schema validator that validates gRPC responses against proto message descriptors.

**Reference**: PRD Section 5.2.2 (Proto Schema Validator)

**Location**: `tck/validators/proto_schema.py`

**Classes to implement**:

1. `ValidationResult(dataclass)`:
   - valid: bool
   - errors: list[str]
   - proto_type: str

2. `ProtoSchemaValidator`:
   - `validate(self, response: ProtoMessage, expected_type: type) -> ValidationResult`:
     Validate proto message against expected type
   - `_validate_nested(self, message: ProtoMessage) -> list[str]`:
     Recursively validate nested messages

**Validation checks**:
- Type checking (isinstance)
- Required field presence (LABEL_REQUIRED)
- Nested message validation (recursive)
- Field constraints from proto definition
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tck/validators/proto_schema.py exists
- [ ] #2 ValidationResult dataclass has valid, errors, proto_type fields
- [ ] #3 validate() correctly type-checks proto messages
- [ ] #4 Required fields are validated as present
- [ ] #5 Nested messages are validated recursively
- [ ] #6 Error messages clearly identify which field failed and why
<!-- AC:END -->
