---
id: TASK-21
title: Generate and validate Java SUT against TCK
status: To Do
assignee: []
created_date: '2026-03-12 15:13'
labels:
  - phase-3
  - java
  - validation
milestone: TCK Scenario System
dependencies:
  - TASK-20
references:
  - sut/java/
  - run_tck.py
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Run the code generator to produce sut/java/, build the generated Quarkus project with Maven, start it, and run the full TCK against it. Fix any issues in the feature files, generator, or templates until the generated SUT passes all applicable TCK tests. This is the end-to-end validation phase.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Generated Java SUT builds successfully with mvn package
- [ ] #2 Generated Java SUT starts and serves agent card at /.well-known/agent-card.json
- [ ] #3 TCK passes against the generated SUT: uv run ./run_tck.py --sut-host http://localhost:9999
- [ ] #4 All three transports work (JSON-RPC, gRPC, HTTP+JSON)
<!-- AC:END -->
