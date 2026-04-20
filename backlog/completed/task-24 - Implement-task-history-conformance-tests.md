---
id: TASK-24
title: Implement task history conformance tests
status: Done
assignee: []
created_date: '2026-04-17 09:00'
labels:
  - conformance-tests
  - task-history
dependencies: []
references:
  - 'specification/specification.md (lines 469, 762-766)'
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add TCK conformance tests for task history behavior as defined in the A2A specification.

The spec defines task history semantics in multiple places:
- `historyLength` parameter controls how much task history is returned in responses (spec line 469)
- Task history contains Messages exchanged during task execution (spec line 762)
- Agents MAY persist messages in task history (spec line 766)
- Clients MUST NOT rely on history persistence unless negotiated out-of-band

Tests should cover:
1. `historyLength` parameter on SendMessage, GetTask, and other operations that accept it
2. Returned task includes `history` field with messages when `historyLength > 0`
3. `historyLength=0` returns no history
4. History ordering (messages in chronological order)
5. History content matches exchanged messages

This requires:
- New Gherkin scenarios in `scenarios/`
- New requirement definitions in `tck/requirements/`
- New compatibility tests in `tests/compatibility/`
- SUT codegen updates to handle history-related behaviors
- Regeneration of all SUTs
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Gherkin scenarios exist for historyLength parameter behavior
- [x] #2 Requirement definitions cover MUST and MAY aspects of task history
- [x] #3 Compatibility tests validate historyLength=0 returns no history
- [x] #4 Compatibility tests validate historyLength>0 returns history with correct messages
- [x] #5 All three transports (JSONRPC, gRPC, HTTP+JSON) are tested
- [x] #6 All SUTs regenerated and passing new tests
<!-- AC:END -->
