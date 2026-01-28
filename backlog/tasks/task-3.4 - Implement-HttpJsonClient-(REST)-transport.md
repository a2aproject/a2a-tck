---
id: task-3.4
title: Implement HttpJsonClient (REST) transport
status: To Do
assignee: []
created_date: '2026-01-28 09:09'
labels:
  - phase-3
  - transport
  - rest
dependencies:
  - task-3.1
parent_task_id: task-3
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the HTTP+JSON (REST) transport client.

**Reference**: PRD Section 5.3.4 (HTTP+JSON Client Implementation)

**Location**: `tck/transport/http_json_client.py`

**Implementation details**:
- Use httpx.Client for HTTP requests
- Map operations to HTTP verbs and paths per A2A spec Section 11:
  - SendMessage: POST /message:send
  - SendStreamingMessage: POST /message:stream
  - GetTask: GET /tasks/{id}
  - ListTasks: GET /tasks
  - CancelTask: POST /tasks/{id}:cancel
  - SubscribeToTask: GET /tasks/{id}/subscribe (SSE)
  - GetExtendedAgentCard: GET /.well-known/agent.json

**Error handling**:
- HTTP status >= 400 indicates error
- Parse Problem Details (RFC 7807) if Content-Type is application/problem+json

**Streaming**:
- Use httpx streaming for SSE responses
- Parse SSE format (same as JSON-RPC)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tck/transport/http_json_client.py exists
- [ ] #2 HttpJsonClient extends BaseTransportClient
- [ ] #3 All operations use correct HTTP verb and path per A2A spec
- [ ] #4 HTTP status codes are checked for errors
- [ ] #5 Problem Details are handled when present
- [ ] #6 SSE streaming works for streaming operations
- [ ] #7 JSON responses are returned as raw_response dict
<!-- AC:END -->
