---
id: TASK-6.8
title: Implement multi-stream ordering conformance tests
status: To Do
assignee: []
created_date: '2026-03-03 09:47'
labels:
  - phase-6
  - testing
  - streaming
dependencies:
  - TASK-6.7
parent_task_id: TASK-6
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement conformance tests for multi-stream ordering requirements that were deferred from TASK-6.7. These tests require concurrent stream coordination.

## Requirements to test

- **STREAM-ORDER-002**: Events broadcast to all active streams
- **STREAM-ORDER-003**: Each stream receives same events in same order
- **STREAM-ORDER-004**: Closing one stream does not affect others

## Approach

These tests require opening multiple concurrent SubscribeToTask streams on the same task and verifying that:
1. All streams receive the same events
2. Events arrive in the same order across streams
3. Cancelling/closing one stream does not interrupt others

This likely requires threading or async coordination to consume multiple streams in parallel.

## Prerequisites

- Use `create_task()` from `tests/compatibility/_task_helpers.py` to create a real task
- Skip if agent does not support streaming
- Cross-transport parametrization (same pattern as test_task_lifecycle.py)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 STREAM-ORDER-002 test verifies events are broadcast to all active streams
- [ ] #2 STREAM-ORDER-003 test verifies each stream receives same events in same order
- [ ] #3 STREAM-ORDER-004 test verifies closing one stream does not affect others
- [ ] #4 All tests pass `make lint` and `make unit-test`
<!-- AC:END -->
