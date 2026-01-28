---
id: task-3.5
title: Implement TransportManager for client orchestration
status: To Do
assignee: []
created_date: '2026-01-28 09:09'
labels:
  - phase-3
  - transport
  - orchestration
dependencies:
  - task-3.2
  - task-3.3
  - task-3.4
parent_task_id: task-3
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the transport manager that orchestrates transport client creation and selection.

**Reference**: PRD Section 5.3 (Transport Layer), Section 4.2 (transport/manager.py)

**Location**: `tck/transport/manager.py`

**Responsibilities**:
- Create transport clients based on configuration
- Select appropriate client for operations
- Manage client lifecycle (connection, cleanup)
- Support testing specific transports or all transports

**Implementation**:
```python
class TransportManager:
    def __init__(self, base_url: str, transports: list[str] | None = None):
        # Create clients for specified transports (or all if None)
        ...
    
    def get_client(self, transport: str) -> BaseTransportClient:
        # Return specific transport client
        ...
    
    def get_all_clients(self) -> dict[str, BaseTransportClient]:
        # Return all configured clients
        ...
    
    def close(self):
        # Cleanup connections
        ...
```

**Default transports**: ["grpc", "jsonrpc", "http+json"]
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tck/transport/manager.py exists
- [ ] #2 TransportManager can create all three transport clients
- [ ] #3 get_client() returns correct client by transport name
- [ ] #4 get_all_clients() returns dict of all configured clients
- [ ] #5 close() properly cleans up connections
- [ ] #6 Works with subset of transports when specified
<!-- AC:END -->
