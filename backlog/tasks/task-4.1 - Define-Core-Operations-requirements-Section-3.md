---
id: TASK-4.1
title: Define Core Operations requirements (Section 3)
status: Done
assignee: []
created_date: '2026-01-28 09:10'
updated_date: '2026-02-26 09:52'
labels:
  - phase-4
  - requirements
  - core-operations
dependencies:
  - task-1.4
parent_task_id: TASK-4
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Define requirements for Core Operations from A2A Specification Section 3.

**Reference**: PRD Section 6 Task 4.1, A2A Spec Section 3

**Location**: `tck/requirements/core_operations.py`

**Operations to cover**:
- SendMessage (Section 3.1)
- SendStreamingMessage (Section 3.1)
- GetTask (Section 3.2)
- ListTasks (Section 3.2)
- CancelTask (Section 3.3)
- SubscribeToTask (Section 3.4)

**For each operation, define**:
- Request structure requirements
- Response structure requirements
- Success criteria
- Error conditions

**Example requirement IDs**: REQ-3.1.1, REQ-3.1.2, REQ-3.2.1, etc.

**Include transport bindings** for each requirement:
- gRPC RPC name
- JSON-RPC method name
- HTTP verb + path
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tck/requirements/core_operations.py exists
- [ ] #2 SendMessage requirements are defined
- [ ] #3 SendStreamingMessage requirements are defined
- [ ] #4 GetTask requirements are defined
- [ ] #5 ListTasks requirements are defined
- [ ] #6 CancelTask requirements are defined
- [ ] #7 SubscribeToTask requirements are defined
- [ ] #8 Each requirement has transport bindings for all three transports
<!-- AC:END -->
