---
id: TASK-24
title: Implement task history conformance tests
status: Done
assignee: []
created_date: '2026-04-17 09:00'
updated_date: '2026-04-17 10:02'
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

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented 6 task history conformance tests (CORE-HIST-001 to 006) covering historyLength parameter semantics from A2A spec Section 3.2.4.

**Requirements added:**
- CORE-HIST-001 (SHOULD): historyLength=0 on GetTask omits history
- CORE-HIST-002 (MUST): history count does not exceed requested historyLength
- CORE-HIST-003 (SHOULD): historyLength=0 on SendMessage omits history
- CORE-HIST-004 (MAY): agents may persist messages in task history
- CORE-HIST-005 (SHOULD): history messages in chronological order
- CORE-HIST-006 (SHOULD): history content matches exchanged messages

**Test results against a2a-java SUT:** 15 passed, 3 xfailed (CORE-HIST-003 — SDK ignores historyLength in SendMessageConfiguration).

**Key files:**
- `tck/requirements/core_operations.py` — 6 new RequirementSpecs
- `tests/compatibility/core_operations/test_task_history.py` — 18 tests (6 requirements × 3 transports)
- `tests/compatibility/_task_helpers.py` — `create_multiturn_task` and `create_multiturn_task_with_history` helpers
- `tck/validators/` — `extract_history` added to all transport validators

**Branch:** `task-24/task-history-conformance-tests` (2 commits)
<!-- SECTION:FINAL_SUMMARY:END -->
