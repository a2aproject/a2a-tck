---
id: TASK-8.4
title: Optimize test execution performance
status: To Do
assignee: []
created_date: '2026-01-28 09:14'
updated_date: '2026-03-12 09:09'
labels:
  - phase-8
  - performance
  - optimization
dependencies: []
parent_task_id: TASK-8
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Review and optimize test execution performance for faster feedback.

**Reference**: PRD Section 6 Task 8.4

**Areas to optimize**:

1. **Connection Reuse**:
   - Use session-scoped fixtures for transport clients
   - Reuse gRPC channels across tests

2. **Parallel Execution**:
   - Enable pytest-xdist if beneficial
   - Ensure tests are parallelizable

3. **Lazy Loading**:
   - Load requirements on demand
   - Defer heavy initialization

4. **Caching**:
   - Cache agent card fetch
   - Cache schema loading

5. **Profiling**:
   - Identify slow tests
   - Optimize hot paths

**Target**: Complete test suite runs in reasonable time (<5 minutes for full suite)

**Consider**: Add `--fast` mode that skips slow tests
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Transport clients use session-scoped fixtures
- [ ] #2 Schema loading is cached
- [ ] #3 Agent card is fetched once per session
- [ ] #4 Full test suite completes in reasonable time
- [ ] #5 No obvious performance bottlenecks remain
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Audit (2026-03-12): Session-scoped fixtures exist for sut_host, agent_card, transport_clients, and validators. Basic caching is in place but no formal profiling or benchmarking has been done. No pytest-xdist or parallel execution setup.
<!-- SECTION:NOTES:END -->
