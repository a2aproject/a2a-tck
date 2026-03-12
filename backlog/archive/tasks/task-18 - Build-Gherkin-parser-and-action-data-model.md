---
id: TASK-18
title: Build Gherkin parser and action data model
status: To Do
assignee: []
created_date: '2026-03-12 15:13'
labels:
  - phase-2
  - codegen
  - parser
milestone: TCK Scenario System
dependencies:
  - TASK-16
  - TASK-17
references:
  - codegen/model.py
  - codegen/parser.py
  - codegen/steps.py
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create `codegen/model.py` (Scenario, Trigger, Action dataclasses) and `codegen/parser.py` (parse .feature files using the `gherkin` Python package). Also create `codegen/steps.py` with a step registry that maps step text patterns (via regex) to Action objects. Actions include: ReturnTask, AddArtifact, RejectWithError, StreamStatusUpdate, StreamArtifact, WaitForTimeout, ReturnMessage.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 codegen/model.py defines Scenario, Trigger, and all Action dataclasses
- [ ] #2 codegen/parser.py parses .feature files and returns list of Scenario objects
- [ ] #3 codegen/steps.py maps all When/Then step patterns to Action objects via regex
- [ ] #4 Unit tests in codegen/tests/test_parser.py and test_steps.py pass
<!-- AC:END -->
