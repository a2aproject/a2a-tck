# TCK Core Agent

A complete A2A agent implementation designed specifically for testing with the A2A Technology Compatibility Kit (TCK). This agent is fully compliant with the A2A specification and supports all core features needed for comprehensive testing.

## Features

- **Task Creation**: Automatically creates tasks when messages are received
- **Task State Management**: Properly transitions through task states (submitted → working → completed)
- **Task Cancellation**: Supports task cancellation with proper state updates
- **Artifact Generation**: Creates artifacts with agent responses
- **Task Persistence**: Uses InMemoryTaskStore for task storage and retrieval
- **Full A2A Compliance**: Implements all required A2A protocol features
- **TCK Optimized**: Designed specifically for A2A TCK testing scenarios

## Getting Started

1. Start the server:

   ```bash
   uv run .
   ```

2. The agent will be available at `http://localhost:9999`

3. Test with curl:

   ```bash
   # Send a message (creates a task)
   curl -X POST http://localhost:9999 \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "method": "message/send",
       "params": {
         "message": {
           "messageId": "test-123",
           "role": "user",
           "taskId": "my-task-123",
           "parts": [{"kind": "text", "text": "Hello"}]
         }
       },
       "id": "test-id"
     }'

   # Retrieve the task
   curl -X POST http://localhost:9999 \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "method": "tasks/get",
       "params": {"id": "my-task-123"},
       "id": "test-id-2"
     }'
   ```

## Purpose

This agent serves as the reference implementation for A2A TCK testing. Unlike basic examples that only return Message objects, this implementation:

- Returns Task objects from `message/send` when appropriate
- Supports `tasks/get` and `tasks/cancel` methods
- Maintains task history and state
- Generates artifacts for responses
- Properly handles task lifecycle events
- Includes test-friendly timing adjustments for TCK scenarios

This makes it the ideal System Under Test (SUT) for comprehensive A2A protocol testing and validation. 