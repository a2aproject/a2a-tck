---
id: TASK-23.2
title: 'Phase 2: Build code generator'
status: Done
assignee: []
created_date: '2026-03-12 15:14'
updated_date: '2026-03-12 15:19'
labels:
  - phase-2
  - codegen
milestone: TCK Scenario System
dependencies: []
parent_task_id: TASK-23
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Build the Python codegen package: Gherkin parser, step registry, action data model, Java emitter with Jinja2 templates, and CLI entry point.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 codegen/ package contains: model.py, parser.py, steps.py, java_emitter.py, generator.py
- [x] #2 Generator uses gherkin Python package for parsing and Jinja2 for Java code templates
- [x] #3 Action model covers: ReturnTask, AddArtifact, RejectWithError, StreamStatusUpdate, StreamArtifact, WaitForTimeout, ReturnMessage
- [x] #4 Generated Java targets a2a-java SDK API: AgentExecutor.execute(RequestContext, AgentEmitter), AgentEmitter methods (submit, startWork, complete, cancel, sendMessage, addArtifact), Part types (TextPart, FilePart, DataPart), A2A error classes
- [x] #5 Generated project includes: TckAgentExecutorProducer.java, TckAgentCardProducer.java, pom.xml, application.properties
- [x] #6 All codegen unit tests pass
<!-- AC:END -->
