---
id: TASK-6.7
title: Implement prerequisite-dependent conformance tests (task factory)
status: To Do
assignee: []
created_date: '2026-03-03 08:29'
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
- [ ] #1 Task factory fixture creates real tasks via SendMessage across all transports
- [ ] #2 GetTask, CancelTask, and SubscribeToTask tests work against real tasks
- [ ] #3 Multi-turn messaging tests (taskId reuse, contextId inference) are implemented
- [ ] #4 Push notification CRUD tests are implemented (skipped when unsupported)
- [ ] #5 Multi-stream ordering tests are implemented
- [ ] #6 All tests pass `make lint` and `make unit-test`
<!-- AC:END -->
