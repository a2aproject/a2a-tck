---
id: TASK-28
title: Add binding equivalence conformance tests (BIND-EQUIV-*)
status: To Do
assignee: []
created_date: '2026-04-30 06:52'
labels:
  - conformance-tests
  - interop
  - coverage-gap
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
4 BIND-EQUIV-* requirements have no test coverage (NOT TESTED in full TCK run of April 30 against Java SUT).

- BIND-EQUIV-001 [MUST]: Functional equivalence across transports
- BIND-EQUIV-002 [MUST]: Same response semantics across bindings
- BIND-EQUIV-003 [MUST]: Error mapping equivalence
- BIND-EQUIV-004 [MUST]: Streaming equivalence

These require cross-transport comparison tests — send the same request via gRPC, JSON-RPC, and HTTP+JSON and verify the responses are semantically equivalent. This is a different testing pattern than single-transport tests.
<!-- SECTION:DESCRIPTION:END -->
