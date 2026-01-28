---
id: task-8.2
title: Write CONTRIBUTING.md development guide
status: To Do
assignee: []
created_date: '2026-01-28 09:14'
labels:
  - phase-8
  - documentation
  - contributing
dependencies: []
parent_task_id: task-8
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Write the contributing guide for developers who want to extend or modify the TCK.

**Reference**: PRD Section 6 Task 8.2

**Location**: `CONTRIBUTING.md` (project root)

**Sections to include**:

1. **Development Setup**:
   - Clone repository
   - Install dev dependencies
   - Run tests locally

2. **Code Style**:
   - Linting with ruff
   - Type checking with mypy
   - Line length and formatting

3. **Adding Requirements**:
   - How to create RequirementSpec
   - Where to place new requirements
   - How to add to registry

4. **Adding Tests**:
   - Test file organization
   - Using fixtures
   - Writing parametrized tests

5. **Adding Transport Support**:
   - Implementing BaseTransportClient
   - Adding validators

6. **Pull Request Process**:
   - Branch naming
   - Commit messages
   - Review process

7. **Release Process**:
   - Version numbering
   - Changelog updates
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 CONTRIBUTING.md exists in project root
- [ ] #2 Development setup instructions are complete
- [ ] #3 Code style guidelines are documented
- [ ] #4 Process for adding requirements is explained
- [ ] #5 Process for adding tests is explained
- [ ] #6 PR process is documented
<!-- AC:END -->
