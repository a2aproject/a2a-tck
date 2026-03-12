---
id: TASK-23.1.1
title: Create core_operations.feature
status: To Do
assignee: []
created_date: '2026-03-12 15:15'
labels:
  - gherkin
  - scenarios
milestone: TCK Scenario System
dependencies: []
references:
  - scenarios/core_operations.feature
  - tck/requirements/core_operations.py
parent_task_id: TASK-23.1
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create `scenarios/core_operations.feature` with Gherkin scenarios for all core TCK requirements. Covers: basic completion (tck-send-001), terminal rejection setup (tck-setup-send-002), unsupported content type (tck-send-003), artifacts (text/file/data parts), message response, input_required state, GetTask/CancelTask setup tasks, blocking/non-blocking modes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 scenarios/core_operations.feature exists with valid Gherkin syntax
- [ ] #2 Every multi-operation TCK requirement has a corresponding setup scenario
- [ ] #3 Step vocabulary covers: complete task, reject with error, add artifact (text/file/data), return message, set task state
- [ ] #4 Scenarios use messageId prefix convention matching tck_id() patterns
<!-- AC:END -->
