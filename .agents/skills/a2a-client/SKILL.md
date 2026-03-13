---
name: a2a-client
description: >
  Interact with remote AI agents using the A2A (Agent-to-Agent) protocol as a client.
  Use this skill whenever the user wants to communicate with an A2A agent, send tasks to
  a remote agent, discover agent capabilities, check task status, or get results from an
  A2A-compatible service. Trigger on mentions of A2A, agent-to-agent, remote agents,
  agent cards, or when the user provides a URL to an A2A agent endpoint.
---

# A2A Client

You are an A2A protocol client. You interact with remote A2A agents by making HTTP requests using `curl`. The A2A protocol (https://a2a-protocol.org) enables standardized communication between AI agents.

## Getting Started

The only thing you need from the user is the **base URL** of the A2A agent (e.g. `http://localhost:8080` or `https://agent.example.com`).

**Always start by discovering the agent** — fetch its AgentCard to understand what it can do before sending any messages.

## Step 1: Discover the Agent

Fetch the AgentCard from the well-known endpoint:

```bash
curl -s <BASE_URL>/.well-known/agent-card.json | jq .
```

The AgentCard tells you:
- **name/description**: What the agent is and does
- **skills**: What tasks it can handle (with example prompts)
- **supported_interfaces**: The endpoint URL and protocol binding to use
- **capabilities**: Whether it supports streaming, push notifications, etc.
- **default_input_modes / default_output_modes**: What content types it accepts/produces

First, show the full raw JSON response to the user so they can see everything the agent exposes. Then present a human-readable summary highlighting the agent's name, skills, capabilities, and supported interfaces.

### Choosing the Protocol Binding

Look at `supported_interfaces` in the AgentCard. Each interface has a `protocol_binding` field:
- **`JSONRPC`**: Use JSON-RPC 2.0 envelopes (see JSON-RPC section below)
- **`HTTP+JSON`**: Use REST-style endpoints (see HTTP+JSON section below)

Use the first supported interface in the list (it's ordered by preference). The `url` field in the interface is the endpoint to send requests to.

## Step 2: Send Messages

This is the core interaction — send a user message to the agent and get a response.

### Using HTTP+JSON Binding

```bash
curl -s -X POST <ENDPOINT_URL>/message:send \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "message_id": "'$(uuidgen | tr A-Z a-z)'",
      "role": "ROLE_USER",
      "parts": [
        {"text": "Your message to the agent"}
      ]
    },
    "configuration": {
      "accepted_output_modes": ["text/plain", "application/json"]
    }
  }' | jq .
```

### Using JSON-RPC Binding

```bash
curl -s -X POST <ENDPOINT_URL> \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "SendMessage",
    "params": {
      "message": {
        "message_id": "'$(uuidgen | tr A-Z a-z)'",
        "role": "ROLE_USER",
        "parts": [
          {"text": "Your message to the agent"}
        ]
      },
      "configuration": {
        "accepted_output_modes": ["text/plain", "application/json"]
      }
    }
  }' | jq .
```

### Understanding the Response

`SendMessage` returns either a **Task** or a **Message**:

- **Task response** (JSON has a `task` field): The agent created a task. Check `task.status.state`:
  - `TASK_STATE_COMPLETED` — Done. Look at `task.artifacts` for the output.
  - `TASK_STATE_WORKING` — Still processing. Automatically poll with GetTask (with a short delay between retries) until the task reaches a terminal state, or suggest using streaming instead.
  - `TASK_STATE_INPUT_REQUIRED` — The agent needs more information. Read the status message and ask the user, then send another message with the same `contextId`.
  - `TASK_STATE_FAILED` / `TASK_STATE_REJECTED` — Something went wrong. Show the error.
- **Message response** (JSON has a `message` field): A direct reply (no task created). Read the `parts` for the content.

Always save the `task.id` and `contextId` from responses — you'll need them for follow-up interactions.

**Note on field naming**: If you use JSON-RPC, use `camelCase` (e.g. `contextId`, `taskId`, `messageId`) and not `snake_case` (e.g. `context_id`, `task_id`, `message_id`).

## Step 3: Streaming (for long-running tasks)

If the agent supports streaming (check `capabilities.streaming` in the AgentCard), use the streaming endpoint for real-time updates.

### Using HTTP+JSON Binding

```bash
curl -s -N -X POST <ENDPOINT_URL>/message:stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": {
      "message_id": "'$(uuidgen | tr A-Z a-z)'",
      "role": "ROLE_USER",
      "parts": [
        {"text": "Your message to the agent"}
      ]
    }
  }'
```

### Using JSON-RPC Binding

```bash
curl -s -N -X POST <ENDPOINT_URL> \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "SendStreamingMessage",
    "params": {
      "message": {
        "message_id": "'$(uuidgen | tr A-Z a-z)'",
        "role": "ROLE_USER",
        "parts": [
          {"text": "Your message to the agent"}
        ]
      }
    }
  }'
```

The response is a Server-Sent Events (SSE) stream. Each event has a `data:` line containing a JSON object with one of:
- `task` — full task snapshot
- `statusUpdate` — task state changed (watch for `TASK_STATE_COMPLETED` or `TASK_STATE_FAILED`)
- `artifactUpdate` — new output chunk (may arrive incrementally with `append: true`)
- `message` — agent message

Use the `-N` flag (no buffering) with curl to see events in real-time.

### Formatting SSE Output

Raw SSE output is hard to read. Pipe the stream through `sed` and `jq` to pretty-print each event as it arrives:

```bash
curl -s -N -X POST <ENDPOINT_URL>/message:stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{ ... }' \
  | grep --line-buffered '^data: ' | sed -u 's/^data: //' | while read -r line; do echo "$line" | jq .; done
```

This extracts only the `data:` lines, strips the prefix, and pretty-prints each JSON payload. Present each formatted event to the user as it arrives, summarizing the state transitions (e.g. "Task submitted → working → completed").

## Step 4: Task Management

### Get Task Status

```bash
# HTTP+JSON
curl -s <ENDPOINT_URL>/tasks/<TASK_ID> | jq .

# JSON-RPC
curl -s -X POST <ENDPOINT_URL> \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"GetTask","params":{"id":"<TASK_ID>"}}' | jq .
```

### List Tasks

```bash
# HTTP+JSON — filter by context
curl -s "<ENDPOINT_URL>/tasks?context_id=<CONTEXT_ID>" | jq .

# JSON-RPC
curl -s -X POST <ENDPOINT_URL> \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"ListTasks","params":{"context_id":"<CONTEXT_ID>"}}' | jq .
```

### Cancel a Task

```bash
# HTTP+JSON
curl -s -X POST <ENDPOINT_URL>/tasks/<TASK_ID>:cancel \
  -H "Content-Type: application/json" \
  -d '{}' | jq .

# JSON-RPC
curl -s -X POST <ENDPOINT_URL> \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"CancelTask","params":{"id":"<TASK_ID>"}}' | jq .
```

## Multi-Turn Conversations

To continue a conversation with an agent:

1. Use the same `context_id` from the previous response
2. Optionally include `task_id` in the message if continuing a specific task
3. Send a new `SendMessage` with the additional input

```bash
curl -s -X POST <ENDPOINT_URL>/message:send \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "message_id": "'$(uuidgen | tr A-Z a-z)'",
      "context_id": "<CONTEXT_ID_FROM_PREVIOUS>",
      "task_id": "<TASK_ID>",
      "role": "ROLE_USER",
      "parts": [
        {"text": "Follow-up message"}
      ]
    }
  }' | jq .
```

This is especially important when the task status is `TASK_STATE_INPUT_REQUIRED` — the agent is waiting for more information.

## Key Principles

- **Always discover first**: Fetch the AgentCard before attempting any interaction.
- **Respect the agent's capabilities**: Don't try streaming if the agent doesn't support it. Use the content types the agent declares.
- **Track context**: Save `task.id` and `context_id` for follow-up messages and task management.
- **Handle all task states**: Not every task completes immediately. Be prepared for `WORKING`, `INPUT_REQUIRED`, and error states.
- **Use `jq` for readability**: Always pipe JSON responses through `jq` for clear output.
- **Generate unique message IDs**: Use `uuidgen` for each message.

## Protocol Reference

The `references/` directory contains the full protocol documentation:

- `references/specification.md` — The complete A2A v1.0.0 specification. Consult this for protocol details, error handling, and edge cases.
- `references/a2a-schema.json` — The JSON Schema for all A2A data types. Use this to validate request/response structures.
- `references/protocol-reference.md` — A quick-reference summary of data types, endpoints, and task lifecycle.
