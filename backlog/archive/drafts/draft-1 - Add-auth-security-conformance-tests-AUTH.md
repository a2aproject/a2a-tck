---
id: DRAFT-1
title: Add auth/security conformance tests (AUTH-*)
status: Draft
assignee: []
created_date: '2026-04-30 06:44'
updated_date: '2026-04-30 06:52'
labels:
  - conformance-tests
  - auth
  - coverage-gap
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add conformance tests for the 13 AUTH-* requirements that have no test coverage:

- AUTH-TLS-001 [MUST]: HTTPS required for production
- AUTH-TLS-002 [SHOULD]: TLS 1.2+ recommended
- AUTH-SERVER-001 [SHOULD]: Server authentication mechanism
- AUTH-SERVER-002 [MUST]: Server auth response format
- AUTH-INTASK-001..004 [MUST]: In-task authentication flow (auth_required state, credentials in message, validation, rejection)
- AUTH-INTASK-005..006 [SHOULD]: Auth token refresh, session management
- AUTH-SCOPE-001..003 [MUST]: Scope-based access control

Note: Some of these (TLS, signing) may be non-automatable and should be documented as such. Focus on the automatable ones first (AUTH-INTASK-*, AUTH-SCOPE-*).
<!-- SECTION:DESCRIPTION:END -->
