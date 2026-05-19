---
id: TASK-23.1
title: 'Phase 1: Create Gherkin feature files'
status: Done
assignee: []
created_date: '2026-03-12 15:14'
updated_date: '2026-03-12 15:19'
labels:
  - phase-1
  - gherkin
milestone: TCK Scenario System
dependencies: []
parent_task_id: TASK-23
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create scenarios/*.feature files defining SUT behavior for all TCK requirements. Each scenario uses When/Then steps mapping to a2a-java AgentEmitter API.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Step vocabulary covers full A2A protocol: task states, parts (text/file/data), artifacts, streaming events (status updates, artifact updates with append/last_chunk), messages, errors
- [x] #2 When steps: 'When a message with prefix ...' and 'When a streaming message with prefix ...'
- [x] #3 Then steps for unary: complete task, set state, return message, add artifact, reject with error
- [x] #4 Then steps for streaming: stream status update, stream artifact, stream artifact append/final chunk, wait for Nx streaming timeout
<!-- AC:END -->
