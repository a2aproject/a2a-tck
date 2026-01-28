---
id: task-8.3
title: Add CI configuration (GitHub Actions)
status: To Do
assignee: []
created_date: '2026-01-28 09:14'
labels:
  - phase-8
  - ci
  - infrastructure
dependencies: []
parent_task_id: task-8
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add GitHub Actions workflow for continuous integration.

**Reference**: PRD Section 6 Task 8.3

**Location**: `.github/workflows/ci.yml`

**Workflow jobs**:

1. **Lint**:
   - Run ruff check
   - Run ruff format --check

2. **Type Check**:
   - Run mypy on tck/ and tests/

3. **Unit Tests**:
   - Run pytest tests/unit/ (no SUT required)

4. **Integration Tests** (optional):
   - If test server available, run full suite
   - Otherwise skip with warning

**Matrix**:
- Python versions: 3.11, 3.12

**Triggers**:
- Push to main
- Pull requests

**Artifacts**:
- Upload test reports
- Upload coverage (if applicable)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 .github/workflows/ci.yml exists
- [ ] #2 Lint job runs ruff check
- [ ] #3 Type check job runs mypy
- [ ] #4 Unit tests run without SUT
- [ ] #5 Python 3.11 and 3.12 are tested
- [ ] #6 Workflow triggers on push and PR
- [ ] #7 CI passes on clean codebase
<!-- AC:END -->
