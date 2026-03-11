---
id: TASK-11.4
title: 'Phase 4: Streaming validators'
status: To Do
assignee: []
created_date: '2026-03-11 16:40'
labels:
  - validators
  - streaming
dependencies:
  - TASK-11.1
parent_task_id: TASK-11
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Attach payload validators to streaming requirements in `tck/requirements/streaming.py` (~8 requirements).

## Validators needed

Streaming has unique validation needs — validators must inspect a *sequence of events*, not a single response.

- **Stream structure validators:**
  - `validate_stream_first_event_is_task()` — first event in task-lifecycle stream is Task
  - `validate_stream_single_message()` — message-only stream has exactly one Message
  - `validate_stream_closes_at_terminal()` — stream closes when task reaches terminal state
  - `validate_stream_event_types()` — events are valid StreamResponse variants (task/message/statusUpdate/artifactUpdate)

- **Event ordering:**
  - `validate_status_updates_monotonic()` — status updates follow valid state transitions

## Design consideration

May need to extend the validator signature or add a separate stream validator type since current validators operate on single responses. Evaluate whether `RequirementSpec.validators` can handle stream event lists or if a new mechanism is needed.

## Key files
- `tck/requirements/streaming.py`
- `tck/validators/payload.py` — may need stream-aware extensions
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All streaming requirements reviewed and validators attached where applicable
- [ ] #2 Stream structure validation covers first-event, closure, and event types
- [ ] #3 Design decision documented if validator signature needs extension
- [ ] #4 make lint and make unit-test pass
<!-- AC:END -->
