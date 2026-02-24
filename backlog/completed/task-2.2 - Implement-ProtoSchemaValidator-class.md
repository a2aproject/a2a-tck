---
id: TASK-2.2
title: Implement ProtoSchemaValidator class
status: Done
assignee: []
created_date: '2026-01-28 09:08'
updated_date: '2026-02-23 14:17'
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
- [x] #1 tck/validators/proto_schema.py exists
- [x] #2 ValidationResult dataclass has valid, errors, proto_type fields
- [x] #3 validate() correctly type-checks proto messages
- [x] #4 Required fields are validated as present
- [x] #5 Nested messages are validated recursively
- [x] #6 Error messages clearly identify which field failed and why
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Implementation Summary

Implemented `tck/validators/proto_schema.py` with:

1. **ValidationResult dataclass** with fields:
   - `valid: bool` - validation result
   - `errors: list[str]` - error messages with field paths
   - `proto_type: str` - the full proto type name

2. **ProtoSchemaValidator class** with:
   - `validate(response, expected_type) -> ValidationResult` - validates proto messages
   - `_validate_message(message, path)` - recursively validates nested messages
   - `_validate_field(message, field_desc, path)` - validates individual fields
   - `_is_field_required(field_desc)` - checks for FIELD_BEHAVIOR_REQUIRED annotation
   - `_is_field_set(message, field_desc, value)` - checks field presence

3. **Key features**:
   - Type checking with isinstance
   - Required field validation using google.api.field_behavior annotation
   - Recursive nested message validation
   - Support for repeated fields and map fields
   - Clear error messages with field paths (e.g., `artifacts[0].artifact_id`)

4. **Tests**: 20 tests covering all acceptance criteria in `tests/validators/test_proto_schema.py`
<!-- SECTION:NOTES:END -->
