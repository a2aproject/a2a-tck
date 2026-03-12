---
id: TASK-23.3
title: 'Phase 3: Generate and validate Java SUT'
status: To Do
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
- [ ] #1 python codegen/generator.py --output sut/java/ produces a complete Quarkus project
- [ ] #2 cd sut/java && mvn package builds successfully
- [ ] #3 Generated SUT starts and serves agent card at /.well-known/agent-card.json
- [ ] #4 uv run ./run_tck.py --sut-host http://localhost:9999 passes all applicable tests
- [ ] #5 All three transports work (JSON-RPC, gRPC, HTTP+JSON)
<!-- AC:END -->
