---
id: TASK-6.7
title: Implement prerequisite-dependent conformance tests (task factory)
status: Done
assignee: []
created_date: '2026-03-03 08:29'
updated_date: '2026-03-03 09:38'
labels:
  - phase-6
  - testing
  - multi-operation
dependencies:
  - TASK-6.6
parent_task_id: TASK-6
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement conformance tests for requirements that need a prerequisite task to exist before the tested operation can run. This requires a **task factory fixture** and multi-step test workflows.

## Problem

Many A2A requirements cannot be tested in isolation — they require a task to have been created first (via `SendMessage`). Currently these are skipped because `sample_input` uses placeholder IDs like `"tck-existing-task"`.

## Scope

### 1. Task factory fixture

Create a pytest fixture (e.g., `existing_task_id`) in `tests/compatibility/conftest.py` that:
- Sends a message via the transport client to create a task
- Extracts and returns the task ID from the response
- Works across all three transports (gRPC protobuf, JSON-RPC dict, HTTP+JSON dict)

Consider also: `terminal_task_id` (a task that has reached a terminal state).

### 2. Requirements to test

**GetTask on real task:**
- CORE-GET-001: GetTask returns current task state

**CancelTask on real task:**
- CORE-CANCEL-001: CancelTask returns updated task with cancellation status
- CORE-CANCEL-002: CancelTask returns TaskNotCancelableError for terminal tasks

**SubscribeToTask on active task:**
- STREAM-SUB-002: SubscribeToTask stream terminates at terminal state
- STREAM-SUB-003: SubscribeToTask rejects terminal tasks

**Multi-turn messaging:**
- CORE-SEND-002: SendMessage rejects messages to terminal tasks
- CORE-MULTI-005: Agent infers contextId from task when only taskId provided
- CORE-MULTI-006: Agent rejects mismatching contextId and taskId

**Push notification CRUD (if agent supports push):**
- PUSH-CREATE-001, PUSH-CREATE-002
- PUSH-GET-001, PUSH-GET-002
- PUSH-LIST-001
- PUSH-DEL-001, PUSH-DEL-002

**Multi-stream ordering:**
- STREAM-ORDER-002: Events broadcast to all active streams
- STREAM-ORDER-003: Each stream receives same events in same order
- STREAM-ORDER-004: Closing one stream does not affect others
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Task factory fixture creates real tasks via SendMessage across all transports
- [x] #2 GetTask, CancelTask, and SubscribeToTask tests work against real tasks
- [x] #3 Multi-turn messaging tests (taskId reuse, contextId inference) are implemented
- [x] #4 Push notification CRUD tests are implemented (skipped when unsupported)
- [ ] #5 Multi-stream ordering tests are implemented
- [x] #6 All tests pass `make lint` and `make unit-test`
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented as a shared helper module + two test files instead of a pytest fixture, following the same self-contained pattern as existing tests.\n\n## Files created\n\n1. `tests/compatibility/_task_helpers.py` — Shared helper module with `create_task()`, `extract_task_id()`, `extract_context_id()` functions and `TaskInfo` dataclass\n2. `tests/compatibility/core_operations/test_task_lifecycle.py` — Cross-transport tests for GetTask, CancelTask, multi-turn, SubscribeToTask lifecycle\n3. `tests/compatibility/core_operations/test_push_notifications.py` — Cross-transport push notification CRUD tests\n\n## Deferred\n- Multi-stream ordering (STREAM-ORDER-002/003/004) — requires concurrent stream coordination, should be a separate task (AC #5 not checked)"
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added cross-transport prerequisite-dependent conformance tests.\n\n## Files created\n- `tests/compatibility/_task_helpers.py` — Shared helper with `create_task()`, `extract_task_id()`, `extract_context_id()` and `TaskInfo` dataclass\n- `tests/compatibility/core_operations/test_task_lifecycle.py` — Tests for CORE-GET-001, CORE-CANCEL-001/002, CORE-SEND-002, CORE-MULTI-005/006, STREAM-SUB-002/003\n- `tests/compatibility/core_operations/test_push_notifications.py` — Tests for PUSH-CREATE-001/002, PUSH-GET-001/002, PUSH-LIST-001, PUSH-DEL-001/002\n\n## Deferred\n- Multi-stream ordering (STREAM-ORDER-002/003/004) — requires concurrent stream coordination, should be a separate task
<!-- SECTION:FINAL_SUMMARY:END -->
