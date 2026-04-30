---
id: DRAFT-5
title: Wire remaining core requirements into test runner
status: Draft
assignee: []
created_date: '2026-04-30 06:44'
updated_date: '2026-04-30 06:52'
labels:
  - conformance-tests
  - core
  - coverage-gap
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
22 core requirements have no dedicated test code and aren't being picked up by the parametrized test runner. Either they need multi-operation test scenarios or their requirement definitions need updating:

**SendMessage/Stream basics:**
- CORE-SEND-001 [MUST]: Basic send message success
- CORE-SEND-003 [MUST]: ContentTypeNotSupportedError for unsupported media
- CORE-STREAM-001..003 [MUST]: Basic streaming operations

**GetTask/ListTasks:**
- CORE-GET-002 [MUST]: GetTask error for nonexistent task
- CORE-LIST-001..005 [MUST]: ListTasks operations (filtering, pagination, authorization)

**Cancel:**
- CORE-CANCEL-003 [MUST]: Cancel error handling

**Execution mode:**
- CORE-EXECUTION-MODE-001..002 [MUST]: Execution mode handling

**Multi-turn:**
- CORE-MULTI-001..004 [MUST/MAY], CORE-MULTI-001a, CORE-MULTI-002a [MUST]: Multi-turn conversation requirements

Investigate whether these should be covered by the parametrized runner (if they have an operation field) or need dedicated multi-operation tests.
<!-- SECTION:DESCRIPTION:END -->
