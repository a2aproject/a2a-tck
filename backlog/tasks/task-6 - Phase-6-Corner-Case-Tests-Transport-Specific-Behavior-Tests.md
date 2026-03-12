---
id: TASK-6
title: 'Phase 6: Corner Case Tests - Transport-Specific Behavior Tests'
status: Done
assignee: []
created_date: '2026-01-28 09:11'
updated_date: '2026-03-12 09:09'
labels:
  - phase-6
  - testing
  - corner-cases
dependencies:
  - task-3
  - task-5
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement transport-specific corner case tests that validate behaviors unique to each transport binding.

**Reference**: PRD Section 6 - Phase 6, Section 5.4.2 (Transport Corner Case Tests)

**Goal**: Complete test coverage for transport-specific error handling, streaming behaviors, and protocol mechanics.

**Key principle**: These tests supplement the core parametrized tests with transport-specific validations that cannot be generalized.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 JSON-RPC error code mappings are tested
- [ ] #2 REST HTTP status code mappings are tested
- [ ] #3 gRPC status code mappings are tested
- [ ] #4 Streaming behaviors are tested per transport
- [ ] #5 Problem Details (RFC 7807) is tested for REST
- [ ] #6 All transport-specific tests pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
All transport-specific behavior tests are implemented: gRPC status codes and streaming (tests/compatibility/grpc/), JSON-RPC error codes and SSE streaming (tests/compatibility/jsonrpc/), HTTP+JSON status codes and Problem Details (tests/compatibility/http_json/).
<!-- SECTION:NOTES:END -->
