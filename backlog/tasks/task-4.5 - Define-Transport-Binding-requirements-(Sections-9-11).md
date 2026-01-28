---
id: task-4.5
title: Define Transport Binding requirements (Sections 9-11)
status: To Do
assignee: []
created_date: '2026-01-28 09:10'
labels:
  - phase-4
  - requirements
  - transport-bindings
dependencies:
  - task-1.4
parent_task_id: task-4
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Define requirements specific to each transport binding from A2A Specification Sections 9-11.

**Reference**: PRD Section 6 Task 4.5, PRD Section 3.4, A2A Spec Sections 9-11

**Locations**:
- `tck/requirements/binding_jsonrpc.py` - JSON-RPC binding
- `tck/requirements/binding_grpc.py` - gRPC binding
- `tck/requirements/binding_rest.py` - REST binding

**Section 9 - JSON-RPC Binding**:
- Method name mappings
- Error code mappings (-32001 to -32009)
- JSON-RPC envelope format
- Header requirements

**Section 10 - gRPC Binding**:
- Service definition conformance
- Status code mappings
- Metadata header requirements
- Streaming RPC format

**Section 11 - REST Binding**:
- Endpoint path mappings
- HTTP verb mappings
- HTTP status code mappings
- Problem Details format (RFC 7807)
- Header requirements

**These are transport-specific corner cases** that supplement the core requirements.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tck/requirements/binding_jsonrpc.py exists
- [ ] #2 tck/requirements/binding_grpc.py exists
- [ ] #3 tck/requirements/binding_rest.py exists
- [ ] #4 JSON-RPC error code requirements are defined
- [ ] #5 gRPC status code requirements are defined
- [ ] #6 REST HTTP status requirements are defined
- [ ] #7 Each binding file covers its specification section completely
<!-- AC:END -->
