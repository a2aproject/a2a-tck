---
id: TASK-23.2.2
title: Build Java code emitter with Jinja2 templates
status: To Do
assignee: []
created_date: '2026-03-12 15:15'
labels:
  - codegen
  - java
milestone: TCK Scenario System
dependencies: []
references:
  - codegen/java_emitter.py
  - codegen/templates/
parent_task_id: TASK-23.2
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create `codegen/java_emitter.py` that generates Java source from Scenario objects using Jinja2 templates. Templates: TckAgentExecutorProducer.java.j2 (AgentExecutor with messageId routing), TckAgentCardProducer.java.j2 (AgentCard with all capabilities), pom.xml.j2 (a2a-java-sdk deps), application.properties.j2 (Quarkus config). Uses a2a-java API: AgentEmitter (submit, startWork, complete, cancel, sendMessage, addArtifact), Part types (TextPart, FilePart, DataPart), A2A errors.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 codegen/java_emitter.py generates valid Java source from Scenario objects
- [ ] #2 Jinja2 templates produce compilable Java targeting a2a-java SDK API
- [ ] #3 Generated executor routes messageId prefixes to correct AgentEmitter calls
- [ ] #4 Generated pom.xml includes correct a2a-java-sdk dependencies
- [ ] #5 Unit tests in codegen/tests/test_java_emitter.py pass
<!-- AC:END -->
