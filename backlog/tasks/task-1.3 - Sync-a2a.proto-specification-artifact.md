---
id: TASK-1.3
title: Sync a2a.proto specification artifact
status: To Do
assignee: []
created_date: '2026-01-28 09:07'
updated_date: '2026-01-28 09:20'
labels:
  - phase-1
  - foundation
  - specification
dependencies: []
parent_task_id: TASK-1
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Copy or sync the canonical a2a.proto file from the A2A specification repository to the local `specification/` directory.

**Reference**: PRD Section 3.2, Section 6 Task 1.3

**Source**: https://github.com/a2aproject/A2A/blob/main/specification/grpc/a2a.proto

**Target**: `specification/a2a.proto`

**Key principle**: The proto file is the source of truth for all data model validation. This must be the official proto from the A2A specification, not a modified version.

**Consider**:
- Document the version/commit hash for traceability in a `specification/info.json` file
- Consider a script or Makefile target for syncing updates
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 specification/a2a.proto exists and matches official A2A spec
- [ ] #2 File contains all core protocol objects: Task, Message, Part, Artifact, AgentCard
- [ ] #3 Proto file is syntactically valid (can be parsed by protoc)
- [ ] #4 Version/source is documented (commit hash or version number)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan

### Steps
1. Fetch the official a2a.proto from A2A repository:
```bash
curl -o specification/a2a.proto \
  https://raw.githubusercontent.com/a2aproject/A2A/main/specification/a2a.proto
```

2. Document the source version:
   - Create `specification/version.json` or add comment to proto
   - Record commit hash or tag & git URL for traceability

3. Validate proto syntax with buildbuf

### Verification
- `specification/a2a.proto` exists
- Contains core types: Task, Message, Part, Artifact, AgentCard
- Proto parses without syntax errors

### Notes
- Consider a `Makefile` target or script for re-syncing when spec updates
- The proto file MUST be the official version, not modified
<!-- SECTION:PLAN:END -->
