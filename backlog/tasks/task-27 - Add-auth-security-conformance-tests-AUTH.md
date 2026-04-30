---
id: TASK-27
title: Add auth/security conformance tests (AUTH-*)
status: To Do
assignee: []
created_date: '2026-04-30 06:52'
labels:
  - conformance-tests
  - auth
  - coverage-gap
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
13 AUTH-* requirements have no test coverage (NOT TESTED in full TCK run of April 30 against Java SUT).

**In-task authentication (6 reqs):**
- AUTH-INTASK-001 [MUST]: auth_required state triggers auth flow
- AUTH-INTASK-002 [MUST]: Credentials in message
- AUTH-INTASK-003 [MUST]: Credential validation
- AUTH-INTASK-004 [MUST]: Invalid credentials rejection
- AUTH-INTASK-005 [SHOULD]: Auth token refresh
- AUTH-INTASK-006 [SHOULD]: Session management

**Scope-based access (3 reqs):**
- AUTH-SCOPE-001..003 [MUST]: Scope-based access control

**Server auth (2 reqs):**
- AUTH-SERVER-001 [SHOULD]: Server authentication mechanism
- AUTH-SERVER-002 [MUST]: Server auth response format

**TLS (2 reqs):**
- AUTH-TLS-001 [MUST]: HTTPS required for production
- AUTH-TLS-002 [SHOULD]: TLS 1.2+ recommended

TLS requirements may need a separate SUT configuration with TLS enabled. In-task auth and scope requirements need SUT scenarios that exercise the auth flow.
<!-- SECTION:DESCRIPTION:END -->
