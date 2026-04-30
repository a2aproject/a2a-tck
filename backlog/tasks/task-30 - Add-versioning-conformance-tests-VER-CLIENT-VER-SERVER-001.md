---
id: TASK-30
title: 'Add versioning conformance tests (VER-CLIENT-*, VER-SERVER-001)'
status: To Do
assignee: []
created_date: '2026-04-30 06:52'
labels:
  - conformance-tests
  - versioning
  - coverage-gap
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
3 versioning requirements have no test coverage (NOT TESTED in full TCK run of April 30 against Java SUT). VER-SERVER-002/003 already pass.

- VER-CLIENT-001 [MUST]: Clients must send A2A-Version header with each request
- VER-CLIENT-002 [MUST]: Patch version numbers must not affect negotiation
- VER-SERVER-001 [MUST]: Agent processes requests using requested version semantics

VER-CLIENT-001/002 are client-side requirements — the TCK client should be verified to send the correct version header. VER-SERVER-001 tests that the server processes requests using the semantics of the requested version.
<!-- SECTION:DESCRIPTION:END -->
