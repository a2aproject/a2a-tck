---
id: TASK-1.4
title: Implement RequirementSpec base class
status: To Do
assignee: []
created_date: '2026-01-28 09:07'
updated_date: '2026-01-28 09:20'
labels:
  - phase-1
  - foundation
  - requirements
dependencies: []
parent_task_id: TASK-1
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the base dataclass for defining specification requirements, following PRD Section 5.1.1.

**Reference**: PRD Section 5.1.1 (RequirementSpec Base Class)

**Location**: `tck/requirements/base.py`

**Classes to implement**:

1. `RequirementLevel(Enum)`:
   - MUST, SHOULD, MAY

2. `OperationType(Enum)`:
   - All operations from PRD: SendMessage, SendStreamingMessage, GetTask, ListTasks, CancelTask, SubscribeToTask
   - Push notification operations
   - GetExtendedAgentCard

3. `TransportBinding(dataclass)`:
   - grpc_rpc: str
   - jsonrpc_method: str
   - http_json_method: str
   - http_json_path: str

4. `RequirementSpec(dataclass)`:
   - All fields from PRD Section 5.1.1
   - id, section, title, level, description, operation, binding
   - proto_request_type, proto_response_type, json_schema_ref
   - sample_input, expected_behavior
   - spec_url, tags
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tck/requirements/base.py exists with all classes
- [ ] #2 RequirementLevel enum has MUST, SHOULD, MAY values
- [ ] #3 OperationType enum has all operation types from PRD
- [ ] #4 TransportBinding dataclass has all transport-specific fields
- [ ] #5 RequirementSpec dataclass has all fields from PRD Section 5.1.1
- [ ] #6 All dataclasses use proper type hints
- [ ] #7 Classes can be imported: from tck.requirements.base import RequirementSpec
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan

### Steps
1. Create `tck/requirements/base.py` with:

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class RequirementLevel(Enum):
    MUST = "MUST"
    SHOULD = "SHOULD"
    MAY = "MAY"

class OperationType(Enum):
    SEND_MESSAGE = "SendMessage"
    SEND_STREAMING_MESSAGE = "SendStreamingMessage"
    GET_TASK = "GetTask"
    LIST_TASKS = "ListTasks"
    CANCEL_TASK = "CancelTask"
    SUBSCRIBE_TO_TASK = "SubscribeToTask"
    CREATE_PUSH_CONFIG = "CreateTaskPushNotificationConfig"
    GET_PUSH_CONFIG = "GetTaskPushNotificationConfig"
    LIST_PUSH_CONFIGS = "ListTaskPushNotificationConfig"
    DELETE_PUSH_CONFIG = "DeleteTaskPushNotificationConfig"
    GET_EXTENDED_AGENT_CARD = "GetExtendedAgentCard"

@dataclass
class TransportBinding:
    grpc_rpc: str
    jsonrpc_method: str
    http_json_method: str
    http_json_path: str

@dataclass
class RequirementSpec:
    id: str
    section: str
    title: str
    level: RequirementLevel
    description: str
    operation: OperationType
    binding: TransportBinding
    proto_request_type: str
    proto_response_type: str
    json_schema_ref: str
    sample_input: dict = field(default_factory=dict)
    expected_behavior: str = ""
    spec_url: str = ""
    tags: list[str] = field(default_factory=list)
```

2. Export in `tck/requirements/__init__.py`:
```python
from tck.requirements.base import (
    RequirementLevel,
    OperationType,
    TransportBinding,
    RequirementSpec,
)
```

### Verification
```python
from tck.requirements.base import RequirementSpec, RequirementLevel
assert RequirementLevel.MUST.value == "MUST"
```
<!-- SECTION:PLAN:END -->
