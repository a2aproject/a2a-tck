---
id: TASK-23.2.1
title: Build Gherkin parser and action data model
status: Done
assignee: []
created_date: '2026-03-12 15:15'
updated_date: '2026-03-16 10:15'
labels:
  - codegen
  - parser
milestone: TCK Scenario System
dependencies: []
references:
  - codegen/model.py
  - codegen/parser.py
  - codegen/steps.py
parent_task_id: TASK-23.2
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create `codegen/model.py` (Scenario, Trigger, Action dataclasses) and `codegen/parser.py` (parse .feature files using the `gherkin` Python package). Also create `codegen/steps.py` with step registry mapping step text patterns (via regex) to Action objects: ReturnTask, AddArtifact, RejectWithError, StreamStatusUpdate, StreamArtifact, WaitForTimeout, ReturnMessage.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 codegen/model.py defines Scenario, Trigger, and all Action dataclasses
- [x] #2 codegen/parser.py parses .feature files and returns list of Scenario objects
- [x] #3 codegen/steps.py maps all When/Then step patterns to Action objects via regex
- [x] #4 Unit tests in codegen/tests/test_parser.py and test_steps.py pass
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
All code already exists and is fully functional:
- `codegen/model.py`: Scenario, Trigger (MessageTrigger, StreamingMessageTrigger), and all Action dataclasses (CompleteTask, AddArtifact, ReturnMessage, RejectWithError, UpdateTaskStatus, StreamStatusUpdate, StreamArtifact, WaitForTimeout)
- `codegen/parser.py`: Parses .feature files via gherkin-official package, returns list of Scenario objects
- `codegen/steps.py`: Regex-based step registry mapping When/Then patterns to Trigger/Action factories
- All 23 unit tests in test_parser.py and test_steps.py pass
<!-- SECTION:FINAL_SUMMARY:END -->
