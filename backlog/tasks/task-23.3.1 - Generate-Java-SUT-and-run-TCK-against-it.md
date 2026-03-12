---
id: TASK-23.3.1
title: Generate Java SUT and run TCK against it
status: To Do
assignee: []
created_date: '2026-03-12 15:15'
labels:
  - java
  - validation
milestone: TCK Scenario System
dependencies: []
references:
  - sut/java/
  - run_tck.py
parent_task_id: TASK-23.3
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Run `python codegen/generator.py --output sut/java/` to produce the Quarkus project. Build with `mvn package`, start the server, and run the full TCK with `uv run ./run_tck.py --sut-host http://localhost:9999`. Iterate on feature files, templates, and generator until all applicable tests pass across all three transports.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Generated Java SUT builds successfully with mvn package
- [ ] #2 Generated SUT serves agent card at /.well-known/agent-card.json
- [ ] #3 TCK passes: uv run ./run_tck.py --sut-host http://localhost:9999
- [ ] #4 All three transports work (JSON-RPC, gRPC, HTTP+JSON)
<!-- AC:END -->
