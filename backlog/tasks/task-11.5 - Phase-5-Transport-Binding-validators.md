---
id: TASK-11.5
title: 'Phase 5: Transport Binding validators'
status: To Do
assignee: []
created_date: '2026-03-11 16:40'
labels:
  - validators
  - transport-bindings
dependencies:
  - TASK-11.1
parent_task_id: TASK-11
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Attach payload validators to transport binding requirements (~21 requirements across 3 bindings).

## JSON-RPC (tck/requirements/binding_jsonrpc.py, ~7 reqs)
- JSONRPC-FMT-001: `validate_jsonrpc_envelope()` (jsonrpc="2.0", id, result/error)
- JSONRPC-FMT-002: Content-Type application/json header check
- JSONRPC-SVC-001: method name is PascalCase
- JSONRPC-ERR-001: error object has code, message fields
- JSONRPC-ERR-002: error code in defined ranges

## gRPC (tck/requirements/binding_grpc.py, ~6 reqs)
- GRPC-ERR-001: ErrorInfo in status.details with domain='a2a-protocol.org'
- GRPC-ERR-002: gRPC status code matches error binding
- GRPC-META-001: service parameters in metadata

## HTTP/JSON (tck/requirements/binding_http_json.py, ~8 reqs)
- HTTP_JSON-ERR-001: RFC 9457 Problem Details structure (type, title, status, detail)
- HTTP_JSON-ERR-002: type URI matches error binding
- HTTP_JSON-STATUS-001: HTTP status code matches error binding
- HTTP_JSON-QP-001: query parameter names use camelCase
- HTTP_JSON-SVC-001: Content-Type application/json header

## Key files
- `tck/requirements/binding_jsonrpc.py`
- `tck/requirements/binding_grpc.py`
- `tck/requirements/binding_http_json.py`
- `tck/validators/{grpc,jsonrpc,http_json}/error_validator.py` — existing error validators to reuse
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All JSON-RPC binding requirements reviewed and validators attached
- [ ] #2 All gRPC binding requirements reviewed and validators attached
- [ ] #3 All HTTP/JSON binding requirements reviewed and validators attached
- [ ] #4 Reuses existing error validators where possible
- [ ] #5 make lint and make unit-test pass
<!-- AC:END -->
