---
id: TASK-31
title: >-
  Add tests for remaining untested requirements (CORE-CAP-004, DM-SERIAL-005,
  GRPC-SVC-003)
status: To Do
assignee: []
created_date: '2026-04-30 06:52'
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
