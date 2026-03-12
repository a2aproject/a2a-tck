---
id: TASK-17
title: Create Gherkin feature files for streaming operations
status: To Do
assignee: []
created_date: '2026-03-12 15:13'
labels:
  - phase-1
  - gherkin
  - scenarios
  - streaming
milestone: TCK Scenario System
dependencies:
  - TASK-16
references:
  - scenarios/streaming.feature
  - tck/requirements/streaming.py
  - docs/SUT_REQUIREMENTS.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create `scenarios/streaming.feature` with Gherkin scenarios for streaming SUT behavior. Covers: basic streaming with status updates (submitted→working→completed), streaming with artifact output, streaming with chunked/appended artifacts, streaming with file artifacts, long-running task for resubscription test (wait for Nx streaming timeout), subscribe lifecycle setup tasks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 scenarios/streaming.feature exists with valid Gherkin syntax
- [ ] #2 Step vocabulary covers: stream status update, stream artifact, stream artifact append/final chunk, wait for timeout
- [ ] #3 Resubscription scenario uses existing test-resubscribe-message-id prefix
- [ ] #4 All streaming-related multi-operation requirements have setup scenarios
<!-- AC:END -->
