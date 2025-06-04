# A2A Specification Structure Analysis

## Markdown Specification Structure (A2A_SPECIFICATION.md)

### Key Sections
1. **Introduction** (§1)
   - Key Goals of A2A (§1.1)
   - Guiding Principles (§1.2)

2. **Core Concepts Summary** (§2)
   - Basic A2A terminology and concepts

3. **Transport and Format** (§3)
   - Transport Protocol (§3.1)
   - Data Format (§3.2) 
   - Streaming Transport (§3.3)

4. **Authentication and Authorization** (§4)
   - Transport Security (§4.1)
   - Server Identity Verification (§4.2)
   - Client/User Identity & Authentication Process (§4.3)
   - Server Responsibilities for Authentication (§4.4)
   - In-Task Authentication (§4.5)
   - Authorization (§4.6)

5. **Agent Discovery: The Agent Card** (§5)
   - Purpose (§5.1)
   - Discovery Mechanisms (§5.2)
   - Recommended Location (§5.3)
   - Security of Agent Cards (§5.4)
   - AgentCard Object Structure (§5.5)

6. **Task Management** (§6)
   - Task lifecycle and states

7. **Methods** (§7)
   - Core A2A JSON-RPC methods

### Requirement Patterns Identified
- **MUST**: 47 occurrences - Mandatory requirements
- **SHOULD**: 23 occurrences - Strong recommendations  
- **MAY**: 8 occurrences - Optional features
- **REQUIRED**: 6 occurrences - Mandatory fields/behaviors
- **RECOMMENDED**: 4 occurrences - Best practices

## JSON Schema Structure (a2a_schema.json)

### Top-Level Definitions
- **A2ARequest**: Union of all supported request types
- **A2AError**: Union of all A2A-specific error types
- **AgentCard**: Core agent metadata structure
- **AgentCapabilities**: Optional feature declarations
- **SecurityScheme**: Authentication scheme definitions

### Core Object Types
1. **AgentCard**
   - Required: capabilities, defaultInputModes, defaultOutputModes, description, name, skills, url, version
   - Optional: provider, documentationUrl, securitySchemes, security, supportsAuthenticatedExtendedCard

2. **Message**
   - Required: kind, messageId, parts, role
   - Optional: contextId, taskId, referenceTaskIds

3. **Task** 
   - Required: contextId, id, kind, status
   - Optional: artifacts, history

4. **Part Objects**
   - TextPart: kind, text
   - FilePart: kind, filename, uri, mimeType
   - DataPart: kind, data

### Error Code Structure
- Standard JSON-RPC errors: -32700 to -32603
- A2A-specific errors: -32000 to -32099
  - TaskNotFoundError: -32001
  - TaskNotCancelableError: -32002
  - PushNotificationNotSupportedError: -32003
  - UnsupportedOperationError: -32004
  - ContentTypeNotSupportedError: -32005
  - InvalidAgentResponseError: -32006

### Method Signatures
- message/send: SendMessageRequest → SendMessageResponse
- message/stream: SendStreamingMessageRequest → SSE stream
- tasks/get: GetTaskRequest → GetTaskResponse
- tasks/cancel: CancelTaskRequest → CancelTaskResponse
- tasks/resubscribe: TaskResubscriptionRequest → SSE stream
- tasks/pushNotificationConfig/set: SetTaskPushNotificationConfigRequest → SetTaskPushNotificationConfigResponse
- tasks/pushNotificationConfig/get: GetTaskPushNotificationConfigRequest → GetTaskPushNotificationConfigResponse

## Key Requirement Categories

### Transport & Protocol Requirements
- HTTP(S) transport mandatory
- JSON-RPC 2.0 compliance required
- HTTPS for production deployments
- SSE for streaming capabilities

### Authentication Requirements  
- Server MUST authenticate all requests
- Standard HTTP auth mechanisms
- Out-of-band credential acquisition
- Support for secondary authentication flows

### Agent Card Requirements
- MUST be available for discovery
- MUST include required fields (name, description, url, version, capabilities, skills, input/output modes)
- Security considerations for sensitive information

### Task Management Requirements
- Unique task IDs
- Defined task states and transitions
- Support for long-running tasks
- Optional streaming and push notification capabilities 