---
id: TASK-6.6
title: Implement gRPC streaming tests
status: Done
assignee: []
created_date: '2026-01-28 09:12'
updated_date: '2026-03-03 08:31'
labels:
  - phase-6
  - testing
  - grpc
  - streaming
dependencies: []
parent_task_id: TASK-6
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement tests for gRPC native streaming behavior.

**Reference**: PRD Section 6 Task 6.6, A2A Spec Section 7/10

**Location**: `tests/compatibility/grpc/test_streaming.py`

**Test class**: `TestGrpcStreaming`

**Tests to implement**:

1. `test_streaming_response_type`:
   - SendStreamingMessage returns stream iterator
   - SubscribeToTask returns stream iterator

2. `test_streaming_message_structure`:
   - Each streamed message is valid proto
   - Messages have correct type

3. `test_streaming_event_ordering`:
   - Events arrive in correct order
   - Final message indicates completion

4. `test_streaming_cancellation`:
   - Client can cancel stream
   - Server handles cancellation gracefully

5. `test_streaming_error_propagation`:
   - Errors during streaming are received
   - gRPC status code is correct

6. `test_streaming_metadata`:
   - Metadata is accessible on stream
   - Required headers are present
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tests/compatibility/grpc/test_streaming.py exists
- [x] #2 Streaming response type validation (GRPC-ERR-003)
- [x] #3 Message structure validation — each event has exactly one StreamResponse payload (GRPC-ERR-003)
- [x] #4 Event ordering test — no state regression, terminal last event (STREAM-ORDER-001)
- [x] #5 Stream cancellation test (GRPC-ERR-003)
- [x] #6 Error propagation — SubscribeToTask with non-existent task returns NOT_FOUND (STREAM-SUB-004)
- [x] #7 SubscribeToTask first event is Task (STREAM-SUB-001)
- [x] #8 make lint and make unit-test pass
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented `tests/compatibility/grpc/test_streaming.py` with 6 tests in `TestGrpcStreaming`:\n\n1. `test_streaming_response_type` (GRPC-ERR-003) — verifies StreamingResponse with is_streaming=True\n2. `test_streaming_message_structure` (GRPC-ERR-003) — each event has exactly one oneof payload field\n3. `test_streaming_event_ordering` (STREAM-ORDER-001) — no state regression, terminal last event\n4. `test_streaming_cancellation` (GRPC-ERR-003) — client-side cancel after first event\n5. `test_streaming_error_propagation` (STREAM-SUB-004) — SubscribeToTask with non-existent ID returns NOT_FOUND\n6. `test_subscribe_first_event_is_task` (STREAM-SUB-001) — first SubscribeToTask event payload is \"task\"\n\nPrerequisite-dependent tests (needing a task factory fixture) were deferred to TASK-6.7.
<!-- SECTION:FINAL_SUMMARY:END -->
