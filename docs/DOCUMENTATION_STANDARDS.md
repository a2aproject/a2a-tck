# Test Documentation Standards

This document defines the documentation standards for all A2A TCK tests to ensure consistency, traceability, and clear specification references.

## Test Documentation Template

Every test function MUST follow this documentation format:

```python
@pytest.mark.category_marker
def test_example_functionality(fixtures):
    """
    CATEGORY: [MANDATORY|CONDITIONAL MANDATORY|QUALITY|OPTIONAL FEATURE]
    Specification: A2A §X.Y.Z / JSON-RPC 2.0 §N.M
    Requirement: "Exact quote from specification with MUST/SHOULD/MAY keyword"
    
    Test validates that [specific behavior description].
    
    Failure Impact: [What happens if this test fails]
    Fix Suggestion: [Actionable steps to resolve failures]
    
    Args:
        fixtures: Description of test fixtures
        
    Asserts:
        - Specific assertion 1
        - Specific assertion 2
    """
```

## Category Documentation Requirements

### MANDATORY Tests
```python
@mandatory_jsonrpc  # or @mandatory_protocol
def test_example():
    """
    MANDATORY: A2A Specification §X.Y - Requirement Title
    
    The specification states: "Servers MUST..." (exact quote)
    
    Test validates core A2A compliance requirement.
    
    Failure Impact: SDK is NOT A2A compliant
    Fix Suggestion: [Specific implementation guidance]
    """
```

### CONDITIONAL MANDATORY Tests (Capabilities)
```python
@optional_capability
def test_streaming_feature():
    """
    CONDITIONAL MANDATORY: A2A Specification §8.1 - Streaming Support
    
    Status: MANDATORY if capabilities.streaming = true
            SKIP if capabilities.streaming = false/missing
            
    The A2A specification states: "IF an agent declares streaming capability,
    it MUST implement message/stream correctly."
    
    Test validates declared streaming capability implementation.
    
    Failure Impact: False advertising - capability declared but broken
    Fix Suggestion: Either implement streaming or remove capability declaration
    """
```

### QUALITY Tests
```python
@quality_production  # or @quality_basic
def test_production_readiness():
    """
    QUALITY PRODUCTION: Production Deployment Readiness
    
    Tests implementation robustness for production environments.
    While not required for A2A compliance, failures indicate
    areas for improvement before production deployment.
    
    Test validates [specific quality aspect].
    
    Failure Impact: Affects production readiness, deployment not recommended
    Fix Suggestion: [Performance/reliability improvement guidance]
    """
```

### OPTIONAL FEATURE Tests
```python
@optional_feature
def test_convenience_feature():
    """
    OPTIONAL FEATURE: A2A Specification §X.Y - Feature Name
    
    Tests optional implementation that enhances user experience
    but is not required for A2A compliance.
    
    Test validates [specific optional behavior].
    
    Failure Impact: Limits feature completeness (perfectly acceptable)
    Fix Suggestion: [Implementation guidance for enhancement]
    """
```

## Specification Reference Format

### A2A Specification References
- **Format**: `A2A §X.Y.Z - Section Title`
- **Examples**:
  - `A2A §2.1 - Agent Card Structure`
  - `A2A §5.1 - Message Send Method`
  - `A2A §7.3 - Task Retrieval`
  - `A2A §8.1 - Message Streaming`

### JSON-RPC 2.0 References
- **Format**: `JSON-RPC 2.0 §N.M - Section Title`
- **Examples**:
  - `JSON-RPC 2.0 §4.1 - Request Object`
  - `JSON-RPC 2.0 §4.2 - Response Object`
  - `JSON-RPC 2.0 §5.1 - Error Codes`

### Combined References
```python
"""
MANDATORY: A2A §5.1 / JSON-RPC 2.0 §4.1 - Message Send Request Validation

The A2A specification requires message/send method (§5.1) and
JSON-RPC 2.0 requires proper request validation (§4.1).
"""
```

## Requirement Citation Standards

### Use Exact Quotes
```python
# ✅ GOOD - Exact specification quote
"""
The specification states: "Servers MUST support the historyLength parameter
in tasks/get requests to limit the number of messages returned."
"""

# ❌ BAD - Paraphrased or interpreted
"""
The specification says servers should support history length limits.
"""
```

### Include RFC 2119 Keywords
Always include the specific requirement level:
- **MUST/SHALL/REQUIRED** → MANDATORY test
- **SHOULD/RECOMMENDED** → QUALITY test  
- **MAY/OPTIONAL** → OPTIONAL FEATURE test

### Conditional Requirements
```python
"""
The specification states: "IF an agent declares 'streaming: true' in capabilities,
it MUST implement the message/stream method correctly."

Logic: If capability not declared → SKIP test (allowed)
       If capability declared → MANDATORY test (must pass)
"""
```

## Test Assertion Documentation

### Document What Each Assertion Validates
```python
def test_agent_card_validation():
    """
    MANDATORY: A2A §2.1 - Agent Card Required Fields
    
    Asserts:
        - Agent Card contains 'version' field (string)
        - Agent Card contains 'name' field (string) 
        - Agent Card contains 'capabilities' field (object)
        - All required fields have correct types per JSON Schema
    """
    # Test implementation with clear assertions
    assert "version" in agent_card, "Agent Card MUST contain version field (A2A §2.1)"
    assert isinstance(agent_card["version"], str), "version MUST be string type"
```

## Error Message Standards

### Specification-Driven Error Messages
```python
# ✅ GOOD - References specification
assert response_code == 200, "A2A §5.1 requires message/send to return HTTP 200"

# ❌ BAD - Generic error message  
assert response_code == 200, "Expected HTTP 200"
```

### Include Fix Guidance in Assertions
```python
assert "historyLength" in task_response, (
    "A2A §7.3 requires historyLength parameter support. "
    "Fix: Implement historyLength handling in DefaultRequestHandler."
)
```

## Test File Organization Standards

### File Header Documentation
```python
"""
A2A TCK Tests - [Category] - [Area]

This module contains [category] tests for [specific area] of the A2A specification.

Specification Coverage:
- A2A §X.Y.Z - Section covered
- JSON-RPC 2.0 §N.M - Section covered

Test Categories:
- MANDATORY: X tests - Core compliance requirements
- CONDITIONAL: Y tests - Capability-dependent requirements  
- QUALITY: Z tests - Production readiness validation
"""
```

### Test Function Ordering
1. **Imports and fixtures** at top
2. **Helper functions** (if needed)
3. **MANDATORY tests** first
4. **CONDITIONAL MANDATORY tests** second
5. **QUALITY tests** third
6. **OPTIONAL FEATURE tests** last

### Marker Application Standards
```python
# Apply most specific marker first
@mandatory_protocol
@pytest.mark.asyncio  # If needed
def test_core_protocol_feature():
    pass

@optional_capability
@pytest.mark.asyncio
def test_streaming_capability():
    pass
```

## Documentation Review Checklist

For every test, verify:

- [ ] **Category clearly identified** (MANDATORY/CONDITIONAL/QUALITY/FEATURE)
- [ ] **Specification section cited** with exact reference format
- [ ] **Requirement quoted exactly** from specification
- [ ] **RFC 2119 keyword included** (MUST/SHOULD/MAY)
- [ ] **Failure impact documented** (compliance/production/feature impact)
- [ ] **Fix suggestion provided** with actionable guidance
- [ ] **Assertions documented** with what each validates
- [ ] **Error messages reference specification** when possible
- [ ] **Proper markers applied** (@mandatory_*, @optional_*, @quality_*)

## Examples of Well-Documented Tests

### Example 1: Mandatory JSON-RPC Test
```python
@mandatory_jsonrpc
def test_rejects_malformed_json(sut_client):
    """
    MANDATORY: JSON-RPC 2.0 §4.2 - JSON Parsing
    
    The specification states: "When a rpc call is made, the Server MUST reply
    with a Response, except for in the case of Notifications. If there are any
    errors parsing the JSON, the response MUST be an error."
    
    Test validates that malformed JSON requests are properly rejected
    with JSON-RPC error response.
    
    Failure Impact: SDK is NOT JSON-RPC 2.0 compliant
    Fix Suggestion: Add JSON parsing validation to request handler
    
    Asserts:
        - Malformed JSON returns error response (not HTTP error)
        - Error code is -32700 (Parse error)
        - Error message indicates JSON parsing failure
    """
    malformed_json = '{"jsonrpc": "2.0", "method": "test", invalid}'
    
    response = sut_client.send_raw_json(malformed_json)
    
    assert "error" in response, "JSON-RPC 2.0 §4.2 requires error response for malformed JSON"
    assert response["error"]["code"] == -32700, "Parse error must use code -32700"
```

### Example 2: Conditional Mandatory Capability Test
```python
@optional_capability
def test_message_stream_basic(agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §8.1 - Message Streaming
    
    Status: MANDATORY if capabilities.streaming = true
            SKIP if capabilities.streaming = false/missing
            
    The specification states: "Agents that declare streaming capability MUST
    implement the message/stream method to provide real-time message delivery."
    
    Test validates that declared streaming capability works correctly.
    
    Failure Impact: False advertising - streaming declared but broken
    Fix Suggestion: Either implement message/stream method or set streaming: false
    
    Asserts:
        - Returns HTTP 200 with Content-Type: text/event-stream
        - Streams valid JSON-RPC responses
        - Terminates stream appropriately
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('streaming'):
        pytest.skip("Streaming capability not declared - test not applicable")
    
    # Test implementation for declared streaming capability
```

This documentation standard ensures every test clearly communicates:
1. **What** it validates (specification requirement)
2. **Why** it matters (compliance/quality impact)
3. **How** to fix failures (actionable guidance)
4. **Where** it comes from (exact specification reference) 