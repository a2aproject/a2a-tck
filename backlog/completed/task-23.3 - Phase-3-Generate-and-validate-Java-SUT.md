---
id: TASK-23.3
title: 'Phase 3: Generate and validate Java SUT'
status: Done
assignee: []
created_date: '2026-03-12 15:14'
updated_date: '2026-03-12 15:19'
labels:
  - phase-3
  - java
  - validation
milestone: TCK Scenario System
dependencies: []
parent_task_id: TASK-23
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Run the generator to produce sut/java/, build the Quarkus project, and run the full TCK against it until all applicable tests pass.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 python codegen/generator.py --output sut/java/ produces a complete Quarkus project
- [x] #2 cd sut/java && mvn package builds successfully
- [x] #3 Generated SUT starts and serves agent card at /.well-known/agent-card.json
- [x] #4 uv run ./run_tck.py --sut-host http://localhost:9999 passes all applicable tests
- [x] #5 All three transports work (JSON-RPC, gRPC, HTTP+JSON)
<!-- AC:END -->
