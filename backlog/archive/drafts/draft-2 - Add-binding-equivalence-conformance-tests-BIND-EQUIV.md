---
id: DRAFT-2
title: Add binding equivalence conformance tests (BIND-EQUIV-*)
status: Draft
assignee: []
created_date: '2026-04-30 06:44'
updated_date: '2026-04-30 06:52'
labels:
  - conformance-tests
  - interop
  - coverage-gap
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add conformance tests for the 4 BIND-EQUIV-* requirements that have no test coverage:

- BIND-EQUIV-001 [MUST]: Functional equivalence across transports
- BIND-EQUIV-002 [MUST]: Same response semantics across bindings
- BIND-EQUIV-003 [MUST]: Error mapping equivalence
- BIND-EQUIV-004 [MUST]: Streaming equivalence

These tests require cross-transport comparison — send the same request via gRPC, JSON-RPC, and HTTP+JSON and verify the responses are semantically equivalent.
<!-- SECTION:DESCRIPTION:END -->
