---
id: TASK-23
title: 'TCK Scenario System: Gherkin SUT Behavior + Generated Java Agent Executor'
status: To Do
assignee: []
created_date: '2026-03-12 15:14'
updated_date: '2026-03-12 15:19'
labels:
  - epic
milestone: TCK Scenario System
dependencies: []
documentation:
  - .claude/plans/velvety-swinging-matsumoto.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Define SUT behavior in Gherkin .feature files and generate a complete runnable Java SUT (Quarkus + a2a-java SDK) from them. The scenarios describe only what the SUT executor should do — standard A2A protocol behavior is handled by the SDK framework. The messageId prefix is the in-band signal linking TCK tests to SUT behavior.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Gherkin .feature files define SUT behavior for all TCK requirements using a fixed step vocabulary
- [ ] #2 A Python code generator reads .feature files and produces a complete runnable Java SUT (Quarkus + a2a-java SDK)
- [ ] #3 The generated Java SUT passes the full TCK across all three transports (JSON-RPC, gRPC, HTTP+JSON)
- [ ] #4 TCK multi-operation tests use deterministic messageId prefixes matching the Gherkin scenarios
- [ ] #5 The messageId prefix is the in-band signal — no side-channel API needed
<!-- AC:END -->
