---
id: TASK-31
title: >-
  Add tests for remaining untested requirements (CORE-CAP-004, DM-SERIAL-005,
  GRPC-SVC-003)
status: Done
assignee: []
created_date: '2026-04-30 06:52'
updated_date: '2026-04-30 08:18'
labels:
  - conformance-tests
  - coverage-gap
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
3 individual requirements have no test coverage (NOT TESTED in full TCK run of April 30 against Java SUT):

- CORE-CAP-004 [MUST]: Required extension missing returns ExtensionSupportRequiredError — needs a test that requests an extension marked required=true that the agent doesn't support
- DM-SERIAL-005 [SHOULD]: Implementations should ignore unrecognized fields — needs a test that sends messages with extra unknown fields and verifies the server processes them without error
- GRPC-SVC-003 [MUST]: gRPC over HTTP/2 with TLS — needs TLS-enabled SUT configuration to verify gRPC uses TLS
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Completed 2026-04-30

Branch: `task-31-add-coverage-tests` (commit c2a8310)

### Tests added:
- **CORE-CAP-004** in `test_error_handling.py`: jsonrpc + http_json tests for unsupported extension error
- **DM-SERIAL-005** in `test_data_model.py`: jsonrpc + http_json tests for ignoring unknown fields (xfail)
- **GRPC-SVC-003** in `test_transport_security.py`: gRPC TLS check (skips in plaintext envs)

### Results against a2a-java SUT:
- CORE-CAP-004: FAIL (SUT doesn't reject unsupported extensions — needs fix in Java SDK)
- DM-SERIAL-005: XFAIL (SUT rejects unknown fields — SHOULD-level)
- GRPC-SVC-003: SKIP (test env uses plaintext)
- NOT TESTED count: 27 → 24
<!-- SECTION:NOTES:END -->
