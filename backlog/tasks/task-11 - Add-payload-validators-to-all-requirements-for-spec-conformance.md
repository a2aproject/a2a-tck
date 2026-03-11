---
id: TASK-11
title: Add payload validators to all requirements for spec conformance
status: To Do
assignee: []
created_date: '2026-03-11 16:36'
labels:
  - validators
  - conformance
  - spec-coverage
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Problem

Only **1 out of 114 requirements** (CORE-MULTI-001a) has a custom payload validator attached via `RequirementSpec.validators`. While schema-level validation (JSON Schema / Proto Schema) and error code validation exist, there is no fine-grained checking that response payloads conform to specific spec constraints.

This means the TCK can confirm an operation *succeeds* or *fails with the right error code*, but cannot verify that the **response content** is correct (e.g., required fields present, enum values valid, timestamps formatted correctly, pagination semantics correct, stream structure valid).

## Goal

Review every requirement and attach payload validators where the spec mandates specific response content. This will significantly increase the TCK's ability to catch non-conformant implementations.

## Scope

114 requirements across 10 sections:
- Core Operations (55 reqs) — `tck/requirements/core_operations.py`
- Data Model (11 reqs) — `tck/requirements/data_model.py`
- Streaming (8 reqs) — `tck/requirements/streaming.py`
- Push Notifications (10 reqs) — `tck/requirements/push_notifications.py`
- Interoperability (13 reqs) — `tck/requirements/interop.py`
- Agent Card (7 reqs) — `tck/requirements/agent_card.py`
- Auth (5 reqs) — `tck/requirements/auth.py`
- JSON-RPC Binding (7 reqs) — `tck/requirements/binding_jsonrpc.py`
- gRPC Binding (6 reqs) — `tck/requirements/binding_grpc.py`
- HTTP/JSON Binding (8 reqs) — `tck/requirements/binding_http_json.py`

## Existing Infrastructure

- `RequirementSpec.validators` field accepts `list[Callable[[Any, str], list[str]]]`
- Transport-agnostic dispatcher in `tck/validators/payload.py`
- Transport-specific payload validators in `tck/validators/{grpc,jsonrpc,http_json}/payload.py`
- Error validators already exist per transport
- JSON Schema and Proto Schema validators run automatically

## Key Files

- `tck/requirements/base.py` — RequirementSpec class
- `tck/validators/payload.py` — transport-agnostic validator factory
- `tests/compatibility/core_operations/test_requirements.py` — test runner that invokes validators
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every requirement has been reviewed and either has validators attached or is documented as not needing one (error-only, not-automatable, or no payload constraint)
- [ ] #2 New validator functions are transport-aware (handle gRPC/JSON-RPC/HTTP+JSON differences)
- [ ] #3 All new validators have unit tests in tests/unit/
- [ ] #4 make lint and make unit-test pass
- [ ] #5 Validator coverage is tracked (number of requirements with validators vs total)
<!-- AC:END -->
