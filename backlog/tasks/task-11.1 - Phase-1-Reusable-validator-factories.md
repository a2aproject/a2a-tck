---
id: TASK-11.1
title: 'Phase 1: Reusable validator factories'
status: To Do
assignee: []
created_date: '2026-03-11 16:40'
labels:
  - validators
  - foundation
dependencies: []
parent_task_id: TASK-11
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Build the reusable, transport-aware validator factory functions in `tck/validators/payload.py` (and transport-specific modules as needed) that subsequent phases will compose and attach to requirements.

## Validators to implement

- **`validate_response_is_task()`** — response contains a Task object (not Message)
- **`validate_response_is_message()`** — response contains a Message object (not Task)
- **`validate_response_is_task_or_message()`** — oneof semantics for SendMessageResponse
- **`validate_task_state(expected_states)`** — TaskState is one of the expected enum values
- **`validate_task_has_required_fields()`** — id, status present in Task
- **`validate_message_has_required_fields()`** — role, parts, messageId present in Message
- **`validate_timestamp_iso8601(field)`** — field value is ISO 8601 with Z suffix
- **`validate_field_absent(field)`** — field is omitted entirely (not null, not empty)
- **`validate_field_equals(field, expected)`** — field matches expected value
- **`validate_camel_case_keys()`** — all JSON keys use camelCase

Each factory returns `Callable[[Any, str], list[str]]` compatible with `RequirementSpec.validators`.

## Key files
- `tck/validators/payload.py` — transport-agnostic dispatcher (extend)
- `tck/validators/{grpc,jsonrpc,http_json}/payload.py` — transport-specific implementations
- `tests/unit/` — unit tests for all new validators
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All listed validator factories are implemented and transport-aware
- [ ] #2 Each validator has unit tests covering gRPC, JSON-RPC, and HTTP+JSON transports
- [ ] #3 Existing validate_message_response_contains_field still works unchanged
- [ ] #4 make lint and make unit-test pass
<!-- AC:END -->
