---
id: task-3.1
title: Implement BaseTransportClient abstract class
status: To Do
assignee: []
created_date: '2026-01-28 09:09'
labels:
  - phase-3
  - transport
  - base
dependencies: []
parent_task_id: task-3
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the abstract base class that defines the interface for all transport clients.

**Reference**: PRD Section 5.3.1 (Base Transport Client)

**Location**: `tck/transport/base.py`

**Classes to implement**:

1. `TransportResponse(dataclass)`:
   - transport: str ("grpc", "jsonrpc", "http+json")
   - success: bool
   - raw_response: Any (native format)
   - error: str | None
   - is_streaming property (returns False)

2. `StreamingResponse(TransportResponse)`:
   - events: Iterator[Any]
   - is_streaming property (returns True)

3. `BaseTransportClient(ABC)`:
   - `__init__(self, base_url: str)`
   - Abstract methods for all A2A operations:
     - send_message(request: dict) -> TransportResponse
     - send_streaming_message(request: dict) -> StreamingResponse
     - get_task(task_id: str) -> TransportResponse
     - list_tasks(params: dict) -> TransportResponse
     - cancel_task(task_id: str) -> TransportResponse
     - subscribe_to_task(task_id: str) -> StreamingResponse
     - get_extended_agent_card() -> TransportResponse
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tck/transport/base.py exists
- [ ] #2 TransportResponse dataclass has transport, success, raw_response, error fields
- [ ] #3 StreamingResponse extends TransportResponse with events iterator
- [ ] #4 BaseTransportClient is an ABC with all abstract methods
- [ ] #5 All A2A operations from PRD are defined as abstract methods
- [ ] #6 Type hints are complete for all methods
<!-- AC:END -->
