---
id: TASK-1.3
title: Sync a2a.proto specification artifact
status: Done
assignee: []
created_date: '2026-01-28 09:07'
updated_date: '2026-02-16 09:45'
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
- [x] #1 specification/a2a.proto exists and matches official A2A spec
- [x] #2 specification/specification.md exists and matches official A2A spec
- [x] #3 File contains all core protocol objects: Task, Message, Part, Artifact, AgentCard
- [x] #4 Proto file is syntactically valid (can be parsed by protoc)
- [x] #5 Version/source is documented (commit hash or version number)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan

### Steps
1. reuse the existing `scripts/update_spec.sh`
    ```bash
    ./scripts/update_spec.sh
    ```
2. Document the source version:
   - Create `specification/version.json`
   - Record commit hash or tag & git URL for traceability

3. Validate proto syntax with buildbuf

### Verification
- `specification/a2a.proto` exists
  - Contains core types: Task, Message, Part, Artifact, AgentCard
  - Proto parses without syntax errors
- `specification/specification.md` exists
- `specification/version.json` exists
- `specification/buf.lock` exists
- `specification/buf.yaml` exists

### Notes
- reuse the existing `scripts/update_spec.sh`
- Consider a `Makefile` target (`spec`)
- The proto file MUST be the official version, not modified
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Synced A2A specification artifacts from GitHub repository:

**Files synced to `specification/`:**
- `a2a.proto` - Protocol buffer definition with all core types
- `specification.md` - Full A2A specification document
- `buf.yaml` and `buf.lock` - Buf configuration files
- `version.json` - Traceability info (commit hash, source URL, timestamp)

**Core types verified in proto:**
- Task, Message, Part, Artifact, AgentCard

**Traceability:**
- Source: https://github.com/a2aproject/A2A
- Commit: f63f6551c5eea8a573ad6111c9963d2200ef9675
- Sync via: `make spec` or `./scripts/update_spec.sh`
<!-- SECTION:FINAL_SUMMARY:END -->
