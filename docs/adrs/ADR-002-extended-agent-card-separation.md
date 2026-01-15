# ADR-002: Separation of Public and Extended Agent Card Access

## Status

**Accepted**

**Date**: 2026-01-15

**Authors**: @jmesnil

## Context

### Problem Statement

Prior to A2A v1.0.0, the TCK did not distinguish between public agent card access and authenticated extended agent card access. This created several issues:

1. **Specification Misalignment**: A2A v1.0.0 explicitly separates public agent card (`.well-known/agent-card.json`) from extended agent card (authenticated endpoint)
2. **Security Confusion**: Tests couldn't validate that extended information is properly protected
3. **Method Naming**: Single `get_agent_card()` method was ambiguous about which card it retrieves
4. **Authentication Testing**: Couldn't test that extended card requires authentication

### A2A v1.0.0 Specification Requirements

Per A2A Specification v1.0.0 §5:

**Public Agent Card** (`.well-known/agent-card.json`):
- MUST be publicly accessible without authentication
- Contains basic agent information, capabilities, and endpoints
- Standard OpenAPI/JSON Schema format
- Includes `securitySchemes` declaration
- Transport-agnostic (available as a HTTP GET request)

**Extended Agent Card** (`/extendedAgentCard` or method-based):
- MAY require authentication
- Contains additional agent information only for authenticated clients
- Can include sensitive configuration, extended capabilities, etc.
- Separate endpoint/method from public card
- Transport-dependent (using the `GetExtendedAgentCard` operation)

### Requirements

1. **Clear Separation**: Distinct methods for public vs authenticated card access
2. **Specification Compliance**: Align with A2A v1.0.0 naming and behavior
3. **Authentication Validation**: Enable testing that extended card requires auth
4. **Backward Compatibility**: Minimize breaking changes to existing tests
5. **All Transports**: Implement consistently across JSON-RPC, gRPC, and REST

## Decision

### Implementation Overview

We **separated agent card access into two distinct methods** with clear semantics and authentication expectations:

1. `agent_card_utils.py:fetch_agent_card()` - Public, unauthenticated access, transport-agnostic (HTTP Get request)
2. `get_authenticated_extended_card()` - Extended, authenticated access, transport-dependent

### Architecture

```
┌─────────────────────────────────────────────────────┐
│ BaseTransportClient (Abstract Interface)            │
├─────────────────────────────────────────────────────┤
│                                                     │
│ get_authenticated_extended_card(extra_headers)      │
│   → Extended card, auth recommended/required        │
│   → Maps to: GetExtendedAgentCard method/endpoint   │
└─────────────────────────────────────────────────────┘
           │              │              │
           ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────────┐
    │ JSON-RPC │   │   gRPC   │   │     REST.    │
    ├──────────┤   ├──────────┤   ├──────────────┤
    │ GetExt.. │   │ GetAgent │   │ GET          │
    │ AgentCa..│   │ Card()   │   │ v1 /extended │
    │          │   │ +metadata│   │ dAgentCard   │
    └──────────┘   └──────────┘   └──────────────┘
```

### Method Signatures

#### Extended Agent Card (Authenticated)

```python
def get_authenticated_extended_card(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Get the extended agent card with authentication.

    This endpoint MAY require authentication and returns additional
    agent information only available to authenticated clients.

    Args:
        extra_headers: Optional headers (typically includes auth headers)

    Returns:
        Extended agent card data

    Specification: A2A v1.0.0 §5.6 - Extended Agent Card
    """
```

### Transport-Specific Implementations

#### JSON-RPC Transport

**Extended Card**:
- JSON-RPC method: `GetExtendedAgentCard`
- Includes authentication headers from config

#### gRPC Transport

- gRPC method: `GetExtendedAgentCard`
- Includes authentication headers from config

#### REST Transport

**Extended Card**:
- HTTP GET to `/v1/extendedAgentCard`
- Includes authentication headers

### Design Principles

1. **Clear Intent**: Method names explicitly indicate authentication expectations
2. **Consistent Interface**: Same method signatures across all transports
3. **Spec Alignment**: Maps directly to A2A v1.0.0 specification sections
4. **Testability**: Enables validation of authentication enforcement

## Consequences

### Positive

✅ **Specification Compliance**: Fully aligned with A2A v1.0.0
✅ **Clear Semantics**: No ambiguity about which card is being accessed
✅ **Authentication Testing**: Can validate extended card requires auth
✅ **Security**: Properly separates public and sensitive information
✅ **Maintainability**: Clear method purposes reduce confusion
✅ **Documentation**: Self-documenting API (method names indicate purpose)
✅ **Transport Consistency**: Same behavior across JSON-RPC, gRPC, REST

### Negative

⚠️ **Breaking Change**: Code using old method names needs updates
⚠️ **Migration Effort**: test files required updates
⚠️ **Complexity**: Two methods instead of one (more surface area)

### Neutral

ℹ️ **Test Updates**: Required updating test code across the suite
ℹ️ **Documentation**: Need to explain when to use each method

## Alternatives Considered

### Alternative 1: Single Method with Flag
**Approach**: `get_agent_card(authenticated=False)`
**Rejected Because**:
- Less explicit than separate methods
- Easy to forget the flag
- Doesn't clearly map to specification
- Harder to enforce via type system

### Alternative 2: Automatic Detection
**Approach**: Automatically request extended card if auth headers present
**Rejected Because**:
- Magic behavior is confusing
- Harder to test both paths
- Doesn't allow explicit public card access with auth headers


### Test Updates

Updated test files to use appropriate methods:
- **Public agent card tests**: Use `get_agent_card()`
- **Authentication tests**: Use `get_authenticated_extended_card()`
- **Capability tests**: Use appropriate method based on what's being tested

### Related Commits

- `7e51136` - fix: Separate public and extended agent card access for A2A v1.0.0 (#111)
- `63a4d94` - remove get_agent_card from any transport
- `8c19d0e` - fix: run mandatory tests for all transports (#110)

## Usage Examples

### Accessing Public Agent Card

```python
# Get public agent card (no authentication)
public_card = agent_card_utils.fetch_agent_card(sut_client.base_url)

# Check capabilities
capabilities = public_card.get("capabilities", {})
supports_streaming = capabilities.get("streaming", False)
```

### Accessing Extended Agent Card

```python
# Get extended agent card (with authentication)
extended_card = sut_client.get_authenticated_extended_card(
    extra_headers={"Authorization": "Bearer token123"}
)

# Access extended information
extended_capabilities = extended_card.get("extendedCapabilities", {})
```

### Testing Authentication Enforcement

```python
# Test that extended card requires authentication
def test_extended_card_requires_auth():
    # Should fail without auth
    with pytest.raises(TransportError) as exc:
        client.get_authenticated_extended_card()
    assert exc.value.status_code in (401, 403)

    # Should succeed with auth
    card = client.get_authenticated_extended_card(
        extra_headers={"Authorization": "Bearer valid-token"}
    )
    assert card is not None
```

## Specification Mapping

### A2A v1.0.0 §5.5 - Public Agent Card Discovery

**Specification Text**:
> "The Agent Card MUST be publicly accessible at the well-known URI `/.well-known/agent-card.json`"

**TCK Implementation**:
```python
def get_agent_card(self, extra_headers: Optional[Dict[str, str]] = None):
    # Maps to /.well-known/agent-card.json
    # Public access, no authentication required
```

### A2A v1.0.0 §5.6 - Extended Agent Card

**Specification Text**:
> "Agents MAY provide an extended agent card that contains additional information available only to authenticated clients"

**TCK Implementation**:
```python
def get_authenticated_extended_card(self, extra_headers: Optional[Dict[str, str]] = None):
    # Maps to GetExtendedAgentCard method or /extendedAgentCard endpoint
    # MAY require authentication
```

## Testing Strategy

### Security Test Coverage

The separation enables comprehensive security testing:

1. **Public Card Accessibility**
   - Verify public card is accessible without auth
   - Verify public card at correct endpoint
   - Verify public card contains required fields

2. **Extended Card Protection**
   - Verify extended card requires/accepts authentication
   - Verify extended card returns additional information
   - Verify unauthenticated access is properly rejected (if required)

3. **Information Separation**
   - Verify sensitive info not in public card
   - Verify extended info only in extended card

## References

- [A2A Specification v1.0.0 §5.5 - Agent Card Discovery](https://google.github.io/A2A/specification/#agent-card-discovery)
- [A2A Specification v1.0.0 §5.6 - Extended Agent Card](https://google.github.io/A2A/specification/#extended-agent-card)
- Related ADRs: [ADR-001: Authentication Support](ADR-001-authentication-support.md)
- Pull Request: #111

## Decision Outcome

**Status**: ✅ Accepted and Implemented

This ADR documents the accepted approach for separating public and extended agent card access in the A2A TCK. The implementation successfully aligns with A2A v1.0.0 specification requirements while enabling proper authentication testing.
