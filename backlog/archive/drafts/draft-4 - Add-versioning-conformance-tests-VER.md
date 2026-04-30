---
id: DRAFT-4
title: Add versioning conformance tests (VER-*)
status: Draft
assignee: []
created_date: '2026-04-30 06:44'
updated_date: '2026-04-30 06:52'
labels:
  - conformance-tests
  - versioning
  - coverage-gap
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add conformance tests for 3 versioning requirements with no test coverage:

- VER-CLIENT-001 [MUST]: Client sends version in request
- VER-CLIENT-002 [MUST]: Client version negotiation
- VER-SERVER-001 [MUST]: Server version in response

VER-SERVER-002 and VER-SERVER-003 already have test code in the error handling module. These 3 need dedicated tests or need to be wired into the parametrized runner.
<!-- SECTION:DESCRIPTION:END -->
