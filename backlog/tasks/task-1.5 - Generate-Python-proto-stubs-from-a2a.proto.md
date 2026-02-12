---
id: TASK-1.5
title: Generate Python proto stubs from a2a.proto
status: To Do
assignee: []
created_date: '2026-01-28 09:07'
updated_date: '2026-01-28 09:21'
labels:
  - phase-1
  - foundation
  - proto
dependencies:
  - task-1.3
parent_task_id: TASK-1
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use buildbuf/buf to generate Python code from a2a.proto, producing the message classes and gRPC service stubs.

**Reference**: PRD Section 6 Task 1.4

Reuse the existing script `./scripts/generate_grpc_stubs.sh` and change the output files
**Command**:
```bash
./scripts/generate_grpc_stubs.sh
```

**Output files**:
- `specification/generated/a2a_pb2.py` - Message classes
- `specification/generated/a2a_pb2_grpc.py` - gRPC service stubs

**Consider**: Create a Makefile target or script for regeneration when proto changes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 specification/generated/a2a_pb2.py exists
- [ ] #2 specification/generated/a2a_pb2_grpc.py exists
- [ ] #3 Both files can be imported in Python without errors
- [ ] #4 Message classes (Task, Message, Part, etc.) are accessible
- [ ] #5 A2AServiceStub is available for gRPC client use
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan

### Steps
1. Generate Python stubs from a2a.proto:
```bash
./scripts/generate_grpc_stubs.sh
```

3. Verify imports work:
```python
from specification.generated import a2a_pb2
from specification.generated import a2a_pb2_grpc

# Check key types exist
assert hasattr(a2a_pb2, 'Task')
assert hasattr(a2a_pb2, 'Message')
assert hasattr(a2a_pb2, 'Part')
assert hasattr(a2a_pb2_grpc, 'A2AServiceStub')
```

4. Create a Makefile target for regeneration:
```makefile
.PHONY: proto
proto:
	./scripts/generate_grpc_stubs.sh
```

### Verification
- `specification/generated/a2a_pb2.py` exists
- `specification/generated/a2a_pb2_grpc.py` exists
- Both import without errors
- Message classes accessible: Task, Message, Part, Artifact, AgentCard

<!-- SECTION:PLAN:END -->
