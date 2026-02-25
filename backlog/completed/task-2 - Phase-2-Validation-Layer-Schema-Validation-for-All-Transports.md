---
id: TASK-2
title: 'Phase 2: Validation Layer - Schema Validation for All Transports'
status: Done
assignee: []
created_date: '2026-01-28 09:08'
updated_date: '2026-02-25 08:26'
labels:
  - phase-2
  - validation
  - core
dependencies:
  - task-1
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the validation layer that validates responses against the canonical schema for each transport type.

**Reference**: PRD Section 6 - Phase 2, Section 5.2 (Validation Layer)

**Goal**: Schema validation for all three transports (gRPC, JSON-RPC, REST) with transport-specific error validation.

**Key Principle**: Each transport validates using its native format. No conversion between transports.
- gRPC: Proto message → validate against proto descriptor
- JSON-RPC: JSON → unwrap envelope → validate against JSON Schema
- REST: JSON → validate against JSON Schema
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Validators correctly identify valid responses
- [x] #2 Validators correctly identify invalid responses with clear error messages
- [x] #3 Error messages are actionable (include path to error, expected vs actual)
- [x] #4 Each transport uses its native validation (proto for gRPC, JSON Schema for JSON transports)
- [x] #5 Unit tests pass for all validators
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Phase 2 Validation Layer is complete. All 5 subtasks delivered:\n\n- **TASK-2.1**: JSONSchemaValidator — validates JSON responses against the A2A JSON Schema (Draft 2020-12), with full $ref resolution, multiple error collection, and JSONPath error formatting\n- **TASK-2.2**: ProtoSchemaValidator — validates proto messages against expected types, checks required field annotations, handles nested/repeated/map fields\n- **TASK-2.3**: JSON-RPC error validator — validates JSON-RPC error codes against the 11 A2A-defined error types (Section 9)\n- **TASK-2.4**: HTTP+JSON error validator — validates HTTP status codes with RFC 7807 Problem Details support (Section 11)\n- **TASK-2.5**: 105 unit tests across all 4 validators, all passing\n\nKey design: each transport uses native validation (proto for gRPC, JSON Schema for JSON-RPC and HTTP+JSON), no cross-transport conversion.
<!-- SECTION:FINAL_SUMMARY:END -->
