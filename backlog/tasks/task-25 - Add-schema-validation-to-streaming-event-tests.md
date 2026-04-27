---
id: TASK-25
title: Add schema validation to streaming event tests
status: To Do
assignee: []
created_date: '2026-04-27 13:06'
labels:
  - streaming
  - schema-validation
  - test-coverage
dependencies: []
references:
  - tests/compatibility/grpc/test_streaming.py
  - tests/compatibility/jsonrpc/test_sse_streaming.py
  - tests/compatibility/core_operations/test_stream_ordering.py
  - tests/compatibility/core_operations/test_task_lifecycle.py
  - >-
    tests/compatibility/core_operations/test_push_notifications.py —
    test_delivery_payload_format (reference for how schema validation is done
    today)
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The streaming tests (gRPC, JSON-RPC SSE, stream ordering, task lifecycle) currently check structural properties of StreamResponse events — e.g. "exactly one payload field set", correct event ordering, terminal state detection — but never validate that the individual payload objects (`statusUpdate`, `artifactUpdate`, `task`, `message`) conform to their JSON/proto schemas.

This means malformed payloads (like a `TaskStatusUpdateEvent` with an invalid `final` field) pass all streaming tests undetected. The bug was only caught in the push notification delivery test (PUSH-DELIVER-003) which explicitly validates against the StreamResponse JSON schema.

Adding schema validation to streaming tests would catch schema violations across all event delivery paths, not just webhooks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Streaming tests validate each StreamResponse event payload against the appropriate schema (JSON schema for jsonrpc/http_json, proto schema for gRPC)
- [ ] #2 Schema violations in statusUpdate, artifactUpdate, task, and message payloads are reported as test failures
- [ ] #3 Invalid fields like 'final' on TaskStatusUpdateEvent are caught by streaming tests
<!-- AC:END -->
