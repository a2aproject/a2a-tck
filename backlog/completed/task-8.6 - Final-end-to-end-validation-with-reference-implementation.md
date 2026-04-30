---
id: TASK-8.6
title: Final end-to-end validation with reference implementation
status: Done
assignee: []
created_date: '2026-01-28 09:14'
updated_date: '2026-04-30 07:27'
labels:
  - phase-8
  - validation
  - e2e
dependencies:
  - task-8.1
  - task-8.2
  - task-8.3
  - task-8.4
  - task-8.5
parent_task_id: TASK-8
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Perform final end-to-end validation of the TCK against a real A2A implementation.

**Reference**: PRD Section 6 Task 8.6

**Validation steps**:

1. **Find/Create Reference Implementation**:
   - Use official A2A reference server if available
   - Or use a known-compliant implementation

2. **Run Full Test Suite**:
   - All MUST requirements pass
   - SHOULD requirements show expected warnings
   - MAY requirements skip appropriately

3. **Verify Reports**:
   - JSON report is valid and complete
   - HTML report renders correctly
   - Console summary is accurate

4. **Test All Transports**:
   - gRPC tests pass
   - JSON-RPC tests pass
   - REST tests pass

5. **Document Known Issues**:
   - Any spec ambiguities discovered
   - Any implementation variations

**Success criteria**:
- 100% MUST compatibility on reference implementation
- All reports generate correctly
- No false positives or negatives
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 TCK runs against a reference A2A implementation
- [x] #2 All MUST requirements pass on compliant server
- [x] #3 Reports are generated correctly
- [x] #4 All three transports are validated
- [x] #5 No false positives (passing when should fail)
- [x] #6 No false negatives (failing when should pass)
- [x] #7 Known issues are documented
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## TCK Run — 2026-04-30 (a2a-java SUT)

- **Overall compatibility**: 99.0%
- **MUST compatibility**: 100.0%
- **SHOULD compatibility**: 83.3%
- **MAY compatibility**: 100.0%
- **Tests**: 239 passed, 19 skipped, 3 xfailed, 0 failed
- **Single SHOULD failure**: CORE-HIST-003 — being fixed in the A2A Java SDK codebase, not a TCK issue
- **27 NOT TESTED**: requirements without TCK test coverage yet (AUTH-*, BIND-EQUIV-*, CARD-SIGN-*, VER-CLIENT/SERVER-*, CORE-CAP-004, DM-SERIAL-005, GRPC-SVC-003)
- All three transports validated (JSONRPC, gRPC, HTTP+JSON)
- Reports generated correctly (JSON, HTML, JUnit XML)

## Known Issues

### SHOULD-level failure
- **CORE-HIST-003**: History length parameter not fully honored. Being fixed in the A2A Java SDK codebase — not a TCK issue.

### Requirements without TCK test coverage (27)
These requirements have no test code in the TCK yet. Tracked in backlog tasks:
- **AUTH-\*** (13 requirements) — TASK-27: Auth/security tests require TLS and in-task auth flows
- **BIND-EQUIV-\*** (4 requirements) — TASK-28: Cross-transport equivalence tests
- **CARD-SIGN-\*** (4 requirements) — TASK-29: Agent card JCS signing tests
- **VER-CLIENT-001, VER-CLIENT-002, VER-SERVER-001** (3 requirements) — Out of scope (client-side testing)
- **CORE-CAP-004, DM-SERIAL-005, GRPC-SVC-003** (3 requirements) — TASK-31
<!-- SECTION:NOTES:END -->
