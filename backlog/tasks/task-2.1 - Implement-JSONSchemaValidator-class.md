---
id: task-2.1
title: Implement JSONSchemaValidator class
status: To Do
assignee: []
created_date: '2026-01-28 09:08'
labels:
  - phase-2
  - validation
  - json-schema
dependencies:
  - task-1.6
parent_task_id: task-2
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
- [ ] #1 tck/validators/json_schema.py exists
- [ ] #2 ValidationResult dataclass has valid, errors, schema_ref fields
- [ ] #3 JSONSchemaValidator loads a2a.json without errors
- [ ] #4 validate() method resolves $defs references correctly
- [ ] #5 Validation errors include JSON path (e.g., '$.task.status')
- [ ] #6 All errors are collected, not just the first one
<!-- AC:END -->
