# A2A Protocol Reference (v1.0.0)

Specification: https://a2a-protocol.org/v1.0.0/specification/
Definitions: https://a2a-protocol.org/v1.0.0/definitions/

## Agent Discovery

Agents publish an **AgentCard** at `/.well-known/agent-card.json` (unauthenticated) describing their identity, capabilities, skills, endpoints, and auth requirements.

```bash
curl -s <BASE_URL>/.well-known/agent-card.json | jq .
```

### AgentCard Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | yes | Human-readable agent name |
| description | string | yes | Agent purpose |
| version | string | yes | Agent version |
| supported_interfaces | AgentInterface[] | yes | Ordered list of endpoints |
| capabilities | AgentCapabilities | yes | streaming, push_notifications, extensions |
| default_input_modes | string[] | yes | Accepted input MIME types |
| default_output_modes | string[] | yes | Output MIME types |
| skills | AgentSkill[] | yes | Agent abilities |
| security_schemes | map | no | Auth method declarations |
| security_requirements | SecurityRequirement[] | no | Required auth |
| icon_url | string | no | Agent icon |
| documentation_url | string | no | Docs link |
| provider | AgentProvider | no | Provider info |

### AgentInterface

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| url | string | yes | Absolute HTTPS endpoint URL |
| protocol_binding | string | yes | `JSONRPC`, `GRPC`, or `HTTP+JSON` |
| protocol_version | string | yes | e.g. "1.0" |
| tenant | string | no | Multi-tenancy identifier |

### AgentSkill

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | yes | Unique skill identifier |
| name | string | yes | Human-readable name |
| description | string | yes | What the skill does |
| tags | string[] | yes | Searchable keywords |
| examples | string[] | no | Example prompts |
| input_modes | string[] | no | Override default input modes |
| output_modes | string[] | no | Override default output modes |

---

## HTTP+JSON REST Endpoints

All endpoints support an optional `/{tenant}` prefix.

| Method | HTTP | Path | Body |
|--------|------|------|------|
| SendMessage | POST | `/message:send` | SendMessageRequest |
| SendStreamingMessage | POST | `/message:stream` | SendMessageRequest |
| GetTask | GET | `/tasks/{id}` | - |
| ListTasks | GET | `/tasks` | query params |
| CancelTask | POST | `/tasks/{id}:cancel` | optional metadata |
| SubscribeToTask | GET | `/tasks/{id}:subscribe` | - |
| GetExtendedAgentCard | GET | `/extendedAgentCard` | - |

---

## JSON-RPC Binding

For agents using the `JSONRPC` protocol binding, all calls go to the agent's single endpoint URL as POST requests with a JSON-RPC 2.0 envelope:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "<MethodName>",
  "params": { ... }
}
```

Method names: `SendMessage`, `SendStreamingMessage`, `GetTask`, `ListTasks`, `CancelTask`, `SubscribeToTask`, `GetExtendedAgentCard`.

For streaming methods (`SendStreamingMessage`, `SubscribeToTask`), the response is delivered as Server-Sent Events (SSE), with each event containing a JSON-RPC response in the `data:` field.

---

## Core Data Types

### Task

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | yes | Server-generated unique ID |
| context_id | string | no | Groups related interactions |
| status | TaskStatus | yes | Current state |
| artifacts | Artifact[] | no | Output artifacts |
| history | Message[] | no | Message history |
| metadata | object | no | Custom key-value pairs |

### TaskState (enum)

| Value | Description |
|-------|-------------|
| TASK_STATE_SUBMITTED | Task received, not yet started |
| TASK_STATE_WORKING | Agent is processing |
| TASK_STATE_COMPLETED | Successfully finished |
| TASK_STATE_FAILED | Failed with error |
| TASK_STATE_CANCELED | Canceled by client |
| TASK_STATE_INPUT_REQUIRED | Agent needs more input from client |
| TASK_STATE_REJECTED | Agent refused the task |
| TASK_STATE_AUTH_REQUIRED | Authentication needed |

### TaskStatus

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| state | TaskState | yes | Current state |
| message | Message | no | Status message from agent |
| timestamp | Timestamp | no | ISO 8601 |

### Message

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| message_id | string | yes | Unique message ID |
| context_id | string | no | Context grouping |
| task_id | string | no | Associated task |
| role | Role | yes | `ROLE_USER` or `ROLE_AGENT` |
| parts | Part[] | yes | Content parts |
| metadata | object | no | Custom metadata |
| extensions | string[] | no | Extension URIs |
| reference_task_ids | string[] | no | Referenced tasks |

### Role (enum)

| Value | Description |
|-------|-------------|
| ROLE_USER | Client to server |
| ROLE_AGENT | Server to client |

### Part

A Part contains one of these content types:

| Field | Type | Description |
|-------|------|-------------|
| text | string | Text content |
| raw | bytes (base64) | Binary data |
| url | string | URL reference |
| data | JSON value | Structured data |

Plus optional fields: `metadata`, `filename`, `media_type`.

### Artifact

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| artifact_id | string | yes | Unique within task |
| name | string | no | Human-readable name |
| description | string | no | Description |
| parts | Part[] | yes | Content (at least one) |
| metadata | object | no | Custom metadata |

---

## Request Types

### SendMessageRequest

```json
{
  "message": {
    "message_id": "<uuid>",
    "role": "ROLE_USER",
    "parts": [
      { "text": "Your message here" }
    ]
  },
  "configuration": {
    "accepted_output_modes": ["text/plain"],
    "history_length": 10,
    "return_immediately": false
  },
  "metadata": {}
}
```

### SendMessageConfiguration

| Field | Type | Description |
|-------|------|-------------|
| accepted_output_modes | string[] | MIME types client can handle |
| history_length | int | Max messages to return in history |
| return_immediately | bool | If true, return task without waiting |

### GetTaskRequest

| Field | Type | Required |
|-------|------|----------|
| id | string | yes |
| history_length | int | no |

### ListTasksRequest

| Field | Type | Description |
|-------|------|-------------|
| context_id | string | Filter by context |
| status | TaskState | Filter by state |
| page_size | int | Max results (1-100, default 50) |
| page_token | string | Pagination token |
| history_length | int | Max messages per task |
| status_timestamp_after | Timestamp | Filter by time |
| include_artifacts | bool | Include artifacts |

### CancelTaskRequest

| Field | Type | Required |
|-------|------|----------|
| id | string | yes |
| metadata | object | no |

---

## Streaming Response Types

### StreamResponse (one of)

| Field | Type | Description |
|-------|------|-------------|
| task | Task | Full task state |
| message | Message | Agent message |
| status_update | TaskStatusUpdateEvent | State change |
| artifact_update | TaskArtifactUpdateEvent | Output update |

### TaskStatusUpdateEvent

| Field | Type | Required |
|-------|------|----------|
| task_id | string | yes |
| context_id | string | yes |
| status | TaskStatus | yes |
| metadata | object | no |

### TaskArtifactUpdateEvent

| Field | Type | Required |
|-------|------|----------|
| task_id | string | yes |
| context_id | string | yes |
| artifact | Artifact | yes |
| append | bool | no |
| last_chunk | bool | no |
| metadata | object | no |

---

## Task Lifecycle

```
SUBMITTED --> WORKING --> COMPLETED
                |-------> FAILED
                |-------> CANCELED (via CancelTask)
                |-------> INPUT_REQUIRED (needs more user input, resumable)
                |-------> AUTH_REQUIRED (needs authentication)
                |-------> REJECTED (agent refused)
```

When a task is in `INPUT_REQUIRED` state, the client can send another `SendMessage` with the same `context_id` (and optionally `task_id` in the message) to continue the conversation.
