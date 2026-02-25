---
id: TASK-3.4
title: Implement HttpJsonClient transport
status: Done
assignee: []
created_date: '2026-01-28 09:09'
updated_date: '2026-02-25 13:25'
labels:
  - phase-3
  - transport
  - http_json
dependencies:
  - task-3.1
parent_task_id: TASK-3
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
- [x] #1 tck/transport/http_json_client.py exists
- [x] #2 HttpJsonClient extends BaseTransportClient
- [x] #3 All operations use correct HTTP verb and path per A2A spec
- [x] #4 HTTP status codes are checked for errors
- [x] #5 Problem Details are handled when present
- [x] #6 SSE streaming works for streaming operations
- [x] #7 JSON responses are returned as raw_response dict
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented `tck/transport/http_json_client.py` with `HttpJsonClient` extending `BaseTransportClient`. All A2A operations map to correct HTTP verbs and RESTful URL patterns per spec Section 11. HTTP error responses (status >= 400) are detected and RFC 9457 Problem Details are parsed when `Content-Type: application/problem+json`. SSE streaming is supported for `send_streaming_message` and `subscribe_to_task`. Query parameters use camelCase per spec Section 11.5.
<!-- SECTION:FINAL_SUMMARY:END -->
