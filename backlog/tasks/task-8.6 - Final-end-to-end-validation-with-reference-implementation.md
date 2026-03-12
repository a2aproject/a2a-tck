---
id: task-8.6
title: Final end-to-end validation with reference implementation
status: To Do
assignee: []
created_date: '2026-01-28 09:14'
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
parent_task_id: task-8
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
- [ ] #1 TCK runs against a reference A2A implementation
- [ ] #2 All MUST requirements pass on compliant server
- [ ] #3 Reports are generated correctly
- [ ] #4 All three transports are validated
- [ ] #5 No false positives (passing when should fail)
- [ ] #6 No false negatives (failing when should pass)
- [ ] #7 Known issues are documented
<!-- AC:END -->
