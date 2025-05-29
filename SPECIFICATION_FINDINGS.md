# A2A Specification Findings

## Key Discoveries from Schema Validation

### 1. Message Part Field Name Finding

**JSON Schema Evidence**: TextPart uses 'kind' field with value "text"

**Conclusion**: The specification uses "kind" (not "type")

**Issue Identified**: Some tests in the TCK may incorrectly use "type" instead of "kind"

### 2. Agent Card Required Fields

**From JSON Schema**:
- Required fields: ['capabilities', 'defaultInputModes', 'defaultOutputModes', 'description', 'name', 'skills', 'url', 'version']
- All available fields: ['capabilities', 'defaultInputModes', 'defaultOutputModes', 'description', 'documentationUrl', 'name', 'provider', 'security', 'securitySchemes', 'skills', 'supportsAuthenticatedExtendedCard', 'url', 'version']

**Detailed Field Analysis**:

| Field | Type | Required | In Spec | In SDK | Notes |
|-------|------|----------|---------|--------|-------|
| name | string | Yes | Yes | Yes | |
| description | string | Yes | Yes | Yes | |
| version | string | Yes | Yes | Yes | |
| url | string | Yes | Yes | Yes | |
| capabilities | object | Yes | Yes | Yes | |
| defaultInputModes | array | Yes | Yes | Yes | |
| defaultOutputModes | array | Yes | Yes | Yes | |
| skills | array | Yes | Yes | Yes | |
| documentationUrl | string | No | Yes | Yes | Optional field |
| provider | object | No | Yes | Yes | Optional field |
| security | array | No | Yes | Yes | Optional field |
| securitySchemes | object | No | Yes | Yes | Optional field |
| supportsAuthenticatedExtendedCard | boolean | No | Yes | Yes | Optional field |
| **protocolVersion** | string | **NO** | **NO** | **NO** | **NOT in specification!** |
| **id** | string | **NO** | **NO** | **NO** | **NOT in specification!** |

**Critical Finding**: Tests expecting 'protocolVersion' or 'id' fields are testing for non-specification fields and should be fixed.

**Notable Findings**:
- Fields like 'protocolVersion' and 'id' are NOT in the specification
- The specification includes 'security' and 'securitySchemes' fields
- 'supportsAuthenticatedExtendedCard' is available but not required

### 3. Authentication Requirements

**From A2A Specification Section 4: Authentication and Authorization**

#### Expected HTTP Behavior:
- **Missing auth**: Server MUST return 401 Unauthorized with WWW-Authenticate header
- **Invalid auth**: Server SHOULD return 401 Unauthorized or 403 Forbidden
- **Before JSON-RPC layer**: Yes - HTTP-level authentication required

#### Security Scheme Declaration:
- **Field name**: `securitySchemes` (in Agent Card root)
- **Format**: OpenAPI 3.x Security Scheme objects
- **Supported types**: APIKey, HTTPAuth (Bearer/Basic), OAuth2, OpenIdConnect

#### Server Responsibilities:
According to specification section 4.4:
- **MUST** authenticate every incoming request based on Agent Card requirements
- **SHOULD** use HTTP 401/403 for authentication failures
- **SHOULD** include WWW-Authenticate header with 401 responses

#### Current SUT Implementation:
- ✅ Declares `securitySchemes` in Agent Card
- ✅ Includes `security` array with required schemes
- ❌ **Authentication middleware currently disabled** (line 125: "Remove middleware temporarily")
- ❌ SDK doesn't provide built-in authentication enforcement

### 4. Error Codes Found

| Code | Error Type | Description |
|------|------------|-------------|
| -32001 | TaskNotFoundError | Standard A2A error |
| -32002 | TaskNotCancelableError | Standard A2A error |
| -32003 | PushNotificationNotSupportedError | Standard A2A error |
| -32004 | UnsupportedOperationError | Standard A2A error |
| -32005 | ContentTypeNotSupportedError | Standard A2A error |
| -32006 | InvalidAgentResponseError | Standard A2A error |
| -32600 | InvalidRequestError | JSON-RPC standard |
| -32601 | MethodNotFoundError | JSON-RPC standard |
| -32602 | InvalidParamsError | JSON-RPC standard |
| -32603 | InternalError | JSON-RPC standard |
| -32700 | JSONParseError | JSON-RPC standard |

## Next Steps

Based on these findings:
1. **Field Name Issue**: ✅ FIXED - Updated all tests to use "kind" instead of "type"
2. **Agent Card Issue**: ✅ FIXED - Updated tests to NOT expect 'protocolVersion' or 'id'
3. **Authentication Issue**: Need to address SDK limitation - no built-in auth enforcement
4. **Error Codes**: All error codes are properly defined in the specification 

## History Length Parameter Finding

### A2A Specification Section 7.3: tasks/get

**Specification requirement**: 
> `historyLength`: If positive, requests the server to include up to `N` recent messages in `Task.history`.

### JSON Schema Evidence
```json
{
  "description": "Parameters for querying a task, including optional history length.",
  "properties": {
    "historyLength": {
      "description": "Number of recent messages to be retrieved.",
      "type": "integer"
    },
    "id": {
      "description": "Task id.",
      "type": "string"
    }
  }
}
```

### SDK Reality
**SDK DefaultRequestHandler limitation**: The `historyLength` parameter is completely ignored by the SDK's `DefaultRequestHandler.on_get_task()` method.

### SUT Workaround
✅ **KEPT**: SUT uses `TckCoreRequestHandler` which correctly implements `historyLength`
```python
# If historyLength is specified, limit the history
if params.historyLength is not None and task.history:
    task_copy = deepcopy(task)
    if len(task_copy.history) > params.historyLength:
        task_copy.history = task_copy.history[-params.historyLength:]
    return task_copy
```

### TCK Documentation
✅ **ADDED**: `test_sdk_limitations.py` documents this SDK bug
- `test_sdk_default_handler_history_length_bug`: Marked as xfail, documents SDK limitation
- `test_sut_workaround_implements_history_length_correctly`: Verifies our workaround works

### Decision
Keep the SUT workaround because:
1. Other tests (like `test_state_transitions.py`) depend on `historyLength` working
2. This is needed for proper A2A specification compliance testing
3. Test suite documents the SDK limitation clearly

## A2A Error Codes

### Standard JSON-RPC Errors
| Code | Name | SDK Constant | Description |
|------|------|--------------|-------------|
| -32700 | Parse error | JSONParseError | Invalid JSON payload |
| -32600 | Invalid Request | InvalidRequestError | Request payload validation error |
| -32601 | Method not found | MethodNotFoundError | Method doesn't exist |
| -32602 | Invalid params | InvalidParamsError | Invalid parameters |
| -32603 | Internal error | InternalError | Internal JSON-RPC error |

### A2A-Specific Errors
| Code | Name | SDK Constant | Description |
|------|------|--------------|-------------|
| -32001 | Task Not Found | TaskNotFoundError | Task not found |
| -32002 | Task Not Cancelable | TaskNotCancelableError | Task cannot be canceled |
| -32003 | Push Notification Not Supported | PushNotificationNotSupportedError | Push Notification is not supported |
| -32004 | Unsupported Operation | UnsupportedOperationError | This operation is not supported |
| -32005 | Content Type Not Supported | ContentTypeNotSupportedError | Incompatible content types |
| -32006 | Invalid Agent Response | InvalidAgentResponseError | Invalid agent response |

### Complete Schema Definition
From `error_codes.json`:
```json
{
  "name": "A2AError",
  "code": null,
  "message": null
}
{
  "name": "ContentTypeNotSupportedError",
  "code": -32005,
  "message": "Incompatible content types"
}
{
  "name": "InternalError",
  "code": -32603,
  "message": "Internal error"
}
{
  "name": "InvalidAgentResponseError",
  "code": -32006,
  "message": "Invalid agent response"
}
{
  "name": "InvalidParamsError",
  "code": -32602,
  "message": "Invalid parameters"
}
{
  "name": "InvalidRequestError",
  "code": -32600,
  "message": "Request payload validation error"
}
{
  "name": "JSONParseError",
  "code": -32700,
  "message": "Invalid JSON payload"
}
{
  "name": "JSONRPCError",
  "code": null,
  "message": null
}
{
  "name": "MethodNotFoundError",
  "code": -32601,
  "message": "Method not found"
}
{
  "name": "PushNotificationNotSupportedError",
  "code": -32003,
  "message": "Push Notification is not supported"
}
{
  "name": "TaskNotCancelableError",
  "code": -32002,
  "message": "Task cannot be canceled"
}
{
  "name": "TaskNotFoundError",
  "code": -32001,
  "message": "Task not found"
}
{
  "name": "UnsupportedOperationError",
  "code": -32004,
  "message": "This operation is not supported"
}
```

### Error Code Tools
- **check_error_code.sh**: Script to lookup specific error codes in schema
- **error_codes_table.md**: Formatted table of all error codes
- **error_codes.json**: Raw error definitions from schema

✅ **All error codes are properly defined in the specification.** The error code validation shows that both standard JSON-RPC codes (-32700 to -32603) and A2A-specific codes (-32001 to -32006) are correctly documented. 