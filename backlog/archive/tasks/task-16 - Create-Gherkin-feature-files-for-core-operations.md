---
id: TASK-16
title: Create Gherkin feature files for core operations
status: To Do
assignee: []
created_date: '2026-03-12 15:13'
labels:
  - phase-1
  - gherkin
  - scenarios
milestone: TCK Scenario System
dependencies: []
references:
  - scenarios/core_operations.feature
  - tck/requirements/core_operations.py
  - docs/SUT_REQUIREMENTS.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create `scenarios/core_operations.feature` with Gherkin scenarios defining SUT behavior for all core TCK requirements. Each scenario uses `When a message with prefix "..." is received` and `Then` steps mapping to a2a-java AgentEmitter API calls. Covers: CORE-SEND-001 (basic completion), CORE-SEND-002 setup (complete for terminal rejection), CORE-SEND-003 (reject unsupported content type), artifact scenarios (text, file, data parts), message response, input_required state, GetTask/CancelTask setup tasks, blocking/non-blocking modes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 scenarios/core_operations.feature exists with valid Gherkin syntax
- [ ] #2 Every multi-operation TCK requirement has a corresponding setup scenario
- [ ] #3 Step vocabulary covers: complete task, reject with error, add artifact (text/file/data), return message, set task state
- [ ] #4 Scenarios use messageId prefix convention matching tck_id() patterns
<!-- AC:END -->
