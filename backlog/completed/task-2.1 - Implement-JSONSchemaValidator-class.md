---
id: TASK-2.1
title: Implement JSONSchemaValidator class
status: Done
assignee: []
created_date: '2026-01-28 09:08'
updated_date: '2026-02-18 14:04'
labels:
  - phase-2
  - validation
  - json-schema
dependencies:
  - task-1.6
parent_task_id: TASK-2
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the JSON Schema validator that validates JSON responses against a2a.json schema.

**Reference**: PRD Section 5.2.1 (JSON Schema Validator)

**Location**: `tck/validators/json_schema.py`

**Classes to implement**:

1. `ValidationResult(dataclass)`:
   - valid: bool
   - errors: list[str]
   - schema_ref: str

2. `JSONSchemaValidator`:
   - `__init__(self, schema_path: Path)`: Load a2a.json schema
   - `validate(self, response: dict, schema_ref: str) -> ValidationResult`:
     Validate against specific definition (e.g., "#/$defs/Task")

**Requirements**:
- Use jsonschema library with Draft202012Validator
- Resolve schema references ($ref) correctly
- Return all validation errors, not just the first
- Error messages should include JSON path to the invalid field
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tck/validators/json_schema.py exists
- [x] #2 ValidationResult dataclass has valid, errors, schema_ref fields
- [x] #3 JSONSchemaValidator loads a2a.json without errors
- [x] #4 validate() method resolves $defs references correctly
- [x] #5 Validation errors include JSON path (e.g., '$.task.status')
- [x] #6 All errors are collected, not just the first one
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Implementation Summary

Implemented `tck/validators/json_schema.py` with:

1. **ValidationResult dataclass** with fields:
   - `valid: bool` - validation result
   - `errors: list[str]` - error messages with JSON paths
   - `schema_ref: str` - the schema reference used

2. **JSONSchemaValidator class** with:
   - `__init__(schema_path: Path)` - loads a2a.json schema
   - `validate(response: dict, schema_ref: str) -> ValidationResult` - validates against definitions
   - `get_definition_names() -> list[str]` - returns available definitions

3. **Key features**:
   - Uses Draft202012Validator from jsonschema
   - Resolves custom `$ref` format (e.g., `a2a.v1.Task.jsonschema.json` → `Task`)
   - Supports multiple schema_ref formats (`Task`, `#/definitions/Task`, `#/$defs/Task`)
   - Returns all validation errors (not just first)
   - Error messages include JSON path (e.g., `$.status.state`)

4. **Tests**: 24 tests covering all acceptance criteria in `tests/validators/test_json_schema.py`
<!-- SECTION:NOTES:END -->
