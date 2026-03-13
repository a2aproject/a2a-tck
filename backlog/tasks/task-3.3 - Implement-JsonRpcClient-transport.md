---
id: task-3.3
title: Implement JsonRpcClient transport
status: To Do
assignee: []
created_date: '2026-01-28 09:09'
labels:
  - phase-3
  - transport
  - jsonrpc
dependencies:
  - task-3.1
parent_task_id: task-3
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the JSON-RPC 2.0 over HTTP transport client.

**Reference**: PRD Section 5.3.3 (JSON-RPC Client Implementation)

**Location**: `tck/transport/jsonrpc_client.py`

**Implementation details**:
- Use httpx.Client for HTTP requests
- Implement JSON-RPC 2.0 envelope format:
  ```json
  {"jsonrpc": "2.0", "id": <int>, "method": "<method>", "params": {...}}
  ```
- Auto-increment request ID for each call
- POST to "/" with Content-Type: application/json
- For streaming: Accept: text/event-stream, parse SSE format

**Methods to implement**:
- All abstract methods from BaseTransportClient
- `_next_id() -> int`: Generate unique request IDs
- `_call(method: str, params: dict) -> dict`: Core JSON-RPC call
- `_parse_sse(response) -> Iterator[dict]`: Parse SSE stream

**SSE format**:
```
data: {"jsonrpc": "2.0", ...}

data: {"jsonrpc": "2.0", ...}
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tck/transport/jsonrpc_client.py exists
- [ ] #2 JsonRpcClient extends BaseTransportClient
- [ ] #3 JSON-RPC 2.0 envelope is correctly formatted
- [ ] #4 Request IDs auto-increment
- [ ] #5 All A2A operations are implemented with correct method names
- [ ] #6 JSON-RPC errors (in response) are detected and returned
- [ ] #7 SSE parsing works for streaming operations
<!-- AC:END -->
