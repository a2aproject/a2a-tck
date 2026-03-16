---
id: TASK-23.2.3
title: Create generator CLI entry point
status: Done
assignee: []
created_date: '2026-03-12 15:15'
updated_date: '2026-03-16 10:19'
labels:
  - codegen
milestone: TCK Scenario System
dependencies: []
references:
  - codegen/generator.py
parent_task_id: TASK-23.2
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create `codegen/generator.py` CLI that ties together parser, steps, and java_emitter. Usage: `python codegen/generator.py --output sut/java/`. Reads all scenarios/*.feature files, parses them, resolves steps to actions, invokes Java emitter to generate complete Quarkus project.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 codegen/generator.py CLI accepts --output argument
- [x] #2 Running the generator produces a complete Java project under the output directory
- [x] #3 Generator validates feature files and reports errors for unknown steps
- [x] #4 Unit test in codegen/tests/test_generator.py passes
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
All code already exists and is fully functional:
- `codegen/generator.py` CLI accepts --output and optional --scenarios arguments
- Parses all .feature files, resolves steps, and generates a complete Quarkus project
- Reports errors for missing feature files and unknown steps (ValueError from parser)
- Both unit tests pass
<!-- SECTION:FINAL_SUMMARY:END -->
