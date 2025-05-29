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