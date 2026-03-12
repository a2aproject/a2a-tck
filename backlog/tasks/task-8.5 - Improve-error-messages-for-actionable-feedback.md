---
id: TASK-8.5
title: Improve error messages for actionable feedback
status: To Do
assignee: []
created_date: '2026-01-28 09:14'
updated_date: '2026-03-12 09:09'
labels:
  - phase-8
  - ux
  - errors
dependencies: []
parent_task_id: TASK-8
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Review and improve error messages throughout the TCK for clarity and actionability.

**Reference**: PRD Section 6 Task 8.5

**Areas to review**:

1. **Test Failure Messages**:
   - Include requirement ID and title
   - Include spec URL
   - Show expected vs actual
   - Suggest possible fixes

2. **Validation Errors**:
   - Clear JSON path to error location
   - Expected type/value
   - Actual type/value

3. **Connection Errors**:
   - Clear indication of which transport failed
   - Suggest troubleshooting steps

4. **Configuration Errors**:
   - Missing required options
   - Invalid option values

**Error message template**:
```
FAILED: REQ-3.1.1 (Send Message Operation)
Transport: jsonrpc
Expected: error code -32001
Actual: error code -32000
Spec: https://github.com/a2aproject/A2A/...#311
Suggestion: Verify error code mapping in Section 9
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Test failures include requirement ID and title
- [ ] #2 Test failures include spec URL
- [ ] #3 Validation errors show JSON path
- [ ] #4 Expected vs actual values are shown
- [ ] #5 Error messages suggest possible fixes where applicable
- [ ] #6 Connection errors are clear about which transport failed
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Audit (2026-03-12): Transport-specific error validators exist with structured messages (grpc, jsonrpc, http_json). Test helpers use fail_msg() for formatted output. No formal audit of message quality/clarity for end users has been conducted.
<!-- SECTION:NOTES:END -->
