---
id: TASK-19
title: Build Java code emitter with Jinja2 templates
status: To Do
assignee: []
created_date: '2026-03-12 15:13'
labels:
  - phase-2
  - codegen
  - java
milestone: TCK Scenario System
dependencies:
  - TASK-18
references:
  - codegen/java_emitter.py
  - codegen/templates/
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create `codegen/java_emitter.py` that takes parsed Scenario objects and generates Java source files using Jinja2 templates. Templates: `TckAgentExecutor.java.j2` (AgentExecutor with messageId prefix routing in execute() and cancel()), `TckAgentCardProducer.java.j2` (AgentCard with all capabilities enabled), `pom.xml.j2` (dependencies on a2a-java-sdk modules), `application.properties.j2` (Quarkus config). Generated code uses a2a-java API: AgentEmitter methods (submit, startWork, complete, cancel, sendMessage, addArtifact), Part types (TextPart, FilePart, DataPart), A2A errors.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 codegen/java_emitter.py generates valid Java source from Scenario objects
- [ ] #2 Jinja2 templates produce compilable Java code targeting a2a-java SDK API
- [ ] #3 Generated executor routes messageId prefixes to correct AgentEmitter calls
- [ ] #4 Generated pom.xml includes correct a2a-java-sdk dependencies
- [ ] #5 Unit tests in codegen/tests/test_java_emitter.py pass
<!-- AC:END -->
