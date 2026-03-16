---
name: a2a-client
description: >
  Interact with remote AI agents using the A2A (Agent-to-Agent) protocol as a client.
  Use this skill whenever the user wants to communicate with an A2A agent, send tasks to
  a remote agent, discover agent capabilities, check task status, or get results from an
  A2A-compatible service. Trigger on mentions of A2A, agent-to-agent, remote agents,
  agent cards, or when the user provides a URL to an A2A agent endpoint.
allowed-tools: Bash(scripts/*)
---

# A2A Client

You are an A2A protocol client. You interact with remote A2A agents using the scripts in `scripts/`. The A2A protocol (https://a2a-protocol.org) enables standardized communication between AI agents.

## Getting Started

The only thing you need from the user is the **base URL** of the A2A agent (e.g. `http://localhost:8080` or `https://agent.example.com`).

**Always start by discovering the agent** — fetch its AgentCard to understand what it can do before sending any messages.

## Scripts

All scripts support `--help` for usage details. Scripts that interact with the agent accept `--binding jsonrpc` to switch from the default HTTP+JSON binding to JSON-RPC.

### Discover the Agent

```bash
scripts/discover.sh <BASE_URL>
```

The AgentCard tells you:
- **name/description**: What the agent is and does
- **skills**: What tasks it can handle (with example prompts)
- **supported_interfaces**: The endpoint URL and protocol binding to use
- **capabilities**: Whether it supports streaming, push notifications, etc.
- **default_input_modes / default_output_modes**: What content types it accepts/produces

First, show the full raw JSON response to the user so they can see everything the agent exposes. Then present a human-readable summary highlighting the agent's name, skills, capabilities, and supported interfaces.

#### Choosing the Protocol Binding

Look at `supported_interfaces` in the AgentCard. Each interface has a `protocol_binding` field:
- **`JSONRPC`**: Pass `--binding jsonrpc` to all subsequent script calls
- **`HTTP+JSON`**: This is the default, no flag needed

Use the first supported interface in the list (it's ordered by preference). The `url` field in the interface is the endpoint to send requests to.

### Send a Message

```bash
scripts/send-message.sh [OPTIONS] <ENDPOINT_URL> <MESSAGE_TEXT>
```

Options:
- `--binding jsonrpc` — Use JSON-RPC instead of HTTP+JSON
- `--context-id <ID>` — Context ID for multi-turn conversations
- `--task-id <ID>` — Task ID for continuing a specific task
- `--message-id <ID>` — Custom message ID (default: auto-generated UUID)

Examples:
```bash
# Simple message (HTTP+JSON)
scripts/send-message.sh http://localhost:8080 "Hello, agent!"

# JSON-RPC binding
scripts/send-message.sh --binding jsonrpc http://localhost:8080 "What is 2+2?"

# Multi-turn follow-up
scripts/send-message.sh --context-id ctx-123 http://localhost:8080 "Follow-up"
```

#### Understanding the Response

`SendMessage` returns either a **Task** or a **Message**:

- **Task response** (JSON has a `task` field): The agent created a task. Check `task.status.state`:
  - `TASK_STATE_COMPLETED` — Done. Look at `task.artifacts` for the output.
  - `TASK_STATE_WORKING` — Still processing. Poll with `get-task.sh` (with a short delay between retries) until the task reaches a terminal state, or suggest using streaming instead.
  - `TASK_STATE_INPUT_REQUIRED` — The agent needs more information. Read the status message and ask the user, then send another message with the same `contextId` using `--context-id`.
  - `TASK_STATE_FAILED` / `TASK_STATE_REJECTED` — Something went wrong. Show the error.
- **Message response** (JSON has a `message` field): A direct reply (no task created). Read the `parts` for the content.

Always save the `task.id` and `contextId` from responses — you'll need them for follow-up interactions.

### Send a Streaming Message

If the agent supports streaming (check `capabilities.streaming` in the AgentCard):

```bash
scripts/send-streaming-message.sh [OPTIONS] <ENDPOINT_URL> <MESSAGE_TEXT>
```

Options are the same as `send-message.sh`, plus:
- `--raw` — Show raw SSE output without pretty-printing

By default, the script extracts SSE `data:` lines and pretty-prints each JSON payload. Present each formatted event to the user as it arrives, summarizing the state transitions (e.g. "Task submitted -> working -> completed").

The SSE stream contains events with one of:
- `task` — full task snapshot
- `statusUpdate` — task state changed (watch for `TASK_STATE_COMPLETED` or `TASK_STATE_FAILED`)
- `artifactUpdate` — new output chunk (may arrive incrementally with `append: true`)
- `message` — agent message

### Get Task Status

```bash
scripts/get-task.sh [--binding jsonrpc] <ENDPOINT_URL> <TASK_ID>
```

### List Tasks

```bash
scripts/list-tasks.sh [--binding jsonrpc] <ENDPOINT_URL> <CONTEXT_ID>
```

### Cancel a Task

```bash
scripts/cancel-task.sh [--binding jsonrpc] <ENDPOINT_URL> <TASK_ID>
```

## Key Principles

- **Always discover first**: Fetch the AgentCard before attempting any interaction.
- **Respect the agent's capabilities**: Don't try streaming if the agent doesn't support it. Use the content types the agent declares.
- **Track context**: Save `task.id` and `context_id` for follow-up messages and task management.
- **Handle all task states**: Not every task completes immediately. Be prepared for `WORKING`, `INPUT_REQUIRED`, and error states.
- **Message IDs**: Use the user-provided message ID if they specify one, otherwise the scripts generate a unique one with `uuidgen`.

## Protocol Reference

The `references/` directory contains the full protocol documentation:

- `references/specification.md` — The complete A2A v1.0.0 specification. Consult this for protocol details, error handling, and edge cases.
- `references/a2a-schema.json` — The JSON Schema for all A2A data types. Use this to validate request/response structures.
- `references/protocol-reference.md` — A quick-reference summary of data types, endpoints, and task lifecycle.
