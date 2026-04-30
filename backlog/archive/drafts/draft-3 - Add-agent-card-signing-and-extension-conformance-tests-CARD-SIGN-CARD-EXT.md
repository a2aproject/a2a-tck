---
id: DRAFT-3
title: >-
  Add agent card signing and extension conformance tests (CARD-SIGN-*,
  CARD-EXT-*)
status: Draft
assignee: []
created_date: '2026-04-30 06:44'
updated_date: '2026-04-30 06:52'
labels:
  - conformance-tests
  - agent-card
  - coverage-gap
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add conformance tests for 6 agent card requirements with no test coverage:

- CARD-SIGN-001..004 [MUST]: JCS signing of agent cards (signature present, valid, verifiable, algorithm)
- CARD-EXT-001..002 [MUST]: Extended agent card support

CARD-SIGN-* may be non-automatable if the SUT doesn't support signing. Document which are automatable vs. which need to be marked as "skip if not declared".
<!-- SECTION:DESCRIPTION:END -->
