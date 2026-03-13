---
id: task-8.1
title: Write README.md with usage instructions
status: To Do
assignee: []
created_date: '2026-01-28 09:14'
labels:
  - phase-8
  - documentation
dependencies: []
parent_task_id: task-8
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Write comprehensive README documentation for the A2A TCK.

**Reference**: PRD Section 6 Task 8.1

**Location**: `README.md` (project root)

**Sections to include**:

1. **Overview**:
   - What is A2A TCK
   - Purpose and scope
   - Specification version

2. **Installation**:
   - Prerequisites (Python 3.11+)
   - pip install instructions
   - Development installation

3. **Quick Start**:
   - Basic usage example
   - Run against a SUT

4. **CLI Reference**:
   - All command-line options
   - Examples for common use cases

5. **Understanding Results**:
   - Compliance levels (MUST/SHOULD/MAY)
   - Report formats
   - Interpreting failures

6. **Transports**:
   - gRPC, JSON-RPC, REST support
   - Transport-specific notes

7. **Extending the TCK**:
   - Adding requirements
   - Adding tests

8. **License and Contributing**:
   - License information
   - Link to CONTRIBUTING.md
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 README.md exists in project root
- [ ] #2 Overview section explains purpose
- [ ] #3 Installation instructions are complete and accurate
- [ ] #4 Quick start example is provided
- [ ] #5 All CLI options are documented
- [ ] #6 Compliance levels are explained
- [ ] #7 Transport support is documented
<!-- AC:END -->
