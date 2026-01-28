---
id: task-3.6
title: Write transport integration tests
status: To Do
assignee: []
created_date: '2026-01-28 09:09'
labels:
  - phase-3
  - transport
  - testing
  - integration
dependencies:
  - task-3.5
parent_task_id: task-3
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Write integration tests for transport clients to verify they can communicate with an A2A server.

**Reference**: PRD Section 6 Task 3.6

**Location**: `tests/integration/test_transports.py`

**Test approach**:
- Tests require a running A2A server (skip if not available)
- Use pytest fixtures for server URL and client setup
- Test basic connectivity and operation execution

**Test coverage**:

1. **Connection tests** (per transport):
   - Client connects without error
   - Client handles connection failure gracefully

2. **Operation tests** (per transport):
   - send_message executes and returns response
   - get_task with valid ID returns task
   - get_task with invalid ID returns error

3. **Streaming tests** (per transport):
   - send_streaming_message returns iterator
   - Events can be consumed from iterator

**Note**: These tests may be marked as `@pytest.mark.integration` and skipped in CI without a test server.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tests/integration/test_transports.py exists
- [ ] #2 Tests are marked with @pytest.mark.integration
- [ ] #3 Tests gracefully skip when no server available
- [ ] #4 Each transport has connection test
- [ ] #5 Each transport has basic operation test
- [ ] #6 Streaming operations are tested
- [ ] #7 Tests can run against any A2A-compliant server
<!-- AC:END -->
