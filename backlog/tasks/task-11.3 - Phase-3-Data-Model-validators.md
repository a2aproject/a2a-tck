---
id: TASK-11.3
title: 'Phase 3: Data Model validators'
status: To Do
assignee: []
created_date: '2026-03-11 16:40'
labels:
  - validators
  - data-model
dependencies:
  - TASK-11.1
parent_task_id: TASK-11
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Attach payload validators to requirements in `tck/requirements/data_model.py` (~8 requirements need validators).

## Requirements to add validators to

**Task structure:**
- DM-TASK-001: `validate_task_has_required_fields()` (id, status)
- DM-TASK-002: `validate_task_state(all valid enum values)`
- DM-STATUS-001: `validate_response_contains_field("status")`, `validate_response_contains_field("status.state")`

**Message structure:**
- DM-MSG-001: `validate_message_has_required_fields()` (role, parts, messageId)
- DM-MSG-002: `validate_role_enum()`

**Part & Artifact:**
- DM-PART-001: `validate_part_oneof()` (exactly one of text/file/data)
- DM-ART-001: `validate_artifact_has_required_fields()` (artifactId, parts)

**Serialization:**
- DM-SERIAL-001: `validate_camel_case_keys()`
- DM-SERIAL-002: `validate_enum_proto_string_format()`
- DM-SERIAL-003: `validate_timestamp_iso8601()`
- DM-SERIAL-004: `validate_required_fields_present()`
- DM-SERIAL-005: behavioral (SHOULD ignore unknown fields) — skip or lightweight

## Key files
- `tck/requirements/data_model.py`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All data model requirements reviewed and validators attached where applicable
- [ ] #2 Enum validators cover all valid TaskState and Role values
- [ ] #3 Timestamp validator checks ISO 8601 with Z suffix
- [ ] #4 make lint and make unit-test pass
<!-- AC:END -->
