---
id: TASK-29
title: Add agent card signing conformance tests (CARD-SIGN-*)
status: To Do
assignee: []
created_date: '2026-04-30 06:52'
labels:
  - conformance-tests
  - agent-card
  - coverage-gap
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
4 CARD-SIGN-* requirements have no test coverage (NOT TESTED in full TCK run of April 30 against Java SUT).

- CARD-SIGN-001 [MUST]: Agent card signature present
- CARD-SIGN-002 [MUST]: Signature valid
- CARD-SIGN-003 [MUST]: Signature verifiable
- CARD-SIGN-004 [MUST]: Algorithm conformance

Note: The Java SUT does not currently declare extendedAgentCard capability. CARD-EXT-001/002 were correctly skipped (not a gap). CARD-SIGN tests may also need to be skipped if the SUT doesn't implement signing, but this needs investigation — these are MUST-level so they should ideally be tested.
<!-- SECTION:DESCRIPTION:END -->
