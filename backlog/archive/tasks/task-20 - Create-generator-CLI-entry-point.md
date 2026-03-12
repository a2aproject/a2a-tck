---
id: TASK-20
title: Create generator CLI entry point
status: To Do
assignee: []
created_date: '2026-03-12 15:13'
labels:
  - phase-2
  - codegen
milestone: TCK Scenario System
dependencies:
  - TASK-18
  - TASK-19
references:
  - codegen/generator.py
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create `codegen/generator.py` — the CLI entry point that ties together parser, steps, and java_emitter. Usage: `python codegen/generator.py --output sut/java/`. Reads all `scenarios/*.feature` files, parses them, resolves steps to actions, and invokes the Java emitter to generate the complete Quarkus project.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 codegen/generator.py CLI accepts --output argument
- [ ] #2 Running the generator produces a complete Java project under the output directory
- [ ] #3 Generator validates feature files and reports errors for unknown steps
- [ ] #4 Unit test in codegen/tests/test_generator.py passes
<!-- AC:END -->
