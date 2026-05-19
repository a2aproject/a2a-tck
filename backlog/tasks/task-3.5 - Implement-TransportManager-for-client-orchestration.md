---
id: TASK-3.5
title: Implement TransportManager for client orchestration
status: Done
assignee: []
created_date: '2026-01-28 09:09'
updated_date: '2026-02-25 14:07'
labels:
  - phase-3
  - transport
  - orchestration
dependencies:
  - task-3.2
  - task-3.3
  - task-3.4
parent_task_id: TASK-3
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
- [x] #1 tck/transport/manager.py exists
- [x] #2 TransportManager can create all three transport clients
- [x] #3 get_client() returns correct client by transport name
- [x] #4 get_all_clients() returns dict of all configured clients
- [x] #5 close() properly cleans up connections
- [x] #6 Works with subset of transports when specified
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented `tck/transport/manager.py` with `TransportManager` class. Uses a factory registry to create clients for grpc, jsonrpc, and http_json transports. Supports creating all or a subset of transports, validates unknown transport names, and provides `get_client()`, `get_all_clients()`, and `close()` for lifecycle management.
<!-- SECTION:FINAL_SUMMARY:END -->
