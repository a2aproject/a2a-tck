# A2A TCK Test Organization Analysis

## Test Categories Structure

### Mandatory Tests (`tests/mandatory/`)
**Purpose**: Core A2A compliance validation (MUST pass)
**Impact**: Failure = NOT A2A compliant

#### JSON-RPC Tests (`tests/mandatory/jsonrpc/`)
- `test_json_rpc_compliance.py` - Basic JSON-RPC 2.0 compliance
- `test_protocol_violations.py` - Protocol violation handling

#### Protocol Tests (`tests/mandatory/protocol/`)
- `test_agent_card.py` - Agent Card structure and availability
- `test_message_send_method.py` - Core message/send functionality
- `test_state_transitions.py` - Task state management  
- `test_tasks_cancel_method.py` - Task cancellation
- `test_tasks_get_method.py` - Task retrieval

### Optional Tests (`tests/optional/`)
**Purpose**: Non-mandatory features and capabilities

#### Capabilities Tests (`tests/optional/capabilities/`)
**Logic**: Conditional mandatory - skip if not declared, mandatory if declared
- `test_agent_card_optional.py` - Optional Agent Card capabilities
- `test_authentication.py` - Authentication protocol tests
- `test_message_send_capabilities.py` - Modality support tests
- `test_push_notification_config_methods.py` - Push notification config
- `test_streaming_methods.py` - SSE streaming methods
- `test_transport_security.py` - Transport security features

#### Quality Tests (`tests/optional/quality/`)
**Purpose**: Production readiness assessment (never blocks compliance)
- `test_edge_cases.py` - Edge case handling
- `test_task_state_quality.py` - Task state management quality

#### Features Tests (`tests/optional/features/`)
**Purpose**: Optional implementation completeness (informational)
- `test_invalid_business_logic.py` - Business logic validation
- `test_reference_task_ids.py` - Reference task ID support
- `test_sdk_limitations.py` - SDK-specific feature tests

## Test Naming Conventions

### File Naming
- Pattern: `test_<feature_area>.py`
- Examples: `test_agent_card.py`, `test_message_send_method.py`

### Function Naming
- Pattern: `test_<specific_feature>`
- Examples: `test_agent_card_available`, `test_mandatory_fields_present`

## Specification Reference Patterns

### Docstring Format
```python
"""
<CATEGORY>: A2A Specification §<section> - <description>

<detailed explanation>

Failure Impact: <impact description>
Fix Suggestion: <optional fix guidance>

Asserts:
    - <assertion 1>
    - <assertion 2>
"""
```

### Reference Categories
- **MANDATORY**: Core A2A compliance requirements
- **CONDITIONAL MANDATORY**: Required if capability declared
- **OPTIONAL CAPABILITY**: Optional feature validation
- **QUALITY BASIC**: Basic quality indicators
- **OPTIONAL FEATURE**: Optional implementation features

### Specification Section References
- **JSON-RPC 2.0 Specification §<section>**: Core protocol compliance
- **A2A Specification §<section>**: A2A protocol requirements

## Test Markers Usage

### Mandatory Markers
- `@mandatory_protocol` - A2A protocol requirements
- `@mandatory_jsonrpc` - JSON-RPC 2.0 compliance

### Optional Markers  
- `@optional_capability` - Capability-dependent tests
- `@optional_feature` - Optional feature tests
- `@quality_basic` - Basic quality tests

## Specification References Count

### By Section
- §2.1 (Agent Card): 5 references
- §4.1-4.4 (Authentication): 6 references  
- §5.1 (Message Protocol): 12 references
- §6.3 (Task States): 2 references
- §7.3-7.4 (Task Methods): 8 references
- §8.1-8.2 (Streaming): 4 references
- §9.1 (Push Notifications): 4 references

### By Category
- MANDATORY: 15 tests
- CONDITIONAL MANDATORY: 8 tests
- OPTIONAL CAPABILITY: 6 tests
- QUALITY BASIC: 2 tests
- OPTIONAL FEATURE: 3 tests

## Test Discovery Patterns

### Fixture Usage
- `sut_client` - SUTClient instance for HTTP requests
- `agent_card_data` - Global Agent Card data fixture
- `valid_text_message_params` - Standard message parameters

### Common Test Patterns
1. **Agent Card Validation**: Fetch and validate structure
2. **Method Testing**: Call JSON-RPC method and validate response
3. **Error Handling**: Test invalid parameters and error responses
4. **Capability Checking**: Skip tests based on declared capabilities
5. **State Validation**: Verify task state transitions

## Integration with Capability System

### Capability-Based Test Logic
- Tests use `@skip_if_capability_not_declared` decorator
- `has_modality_support()` function checks Agent Card modalities
- `CapabilityValidator` class provides capability validation logic

### Conditional Test Execution
- If capability declared → test is MANDATORY
- If capability not declared → test SKIPPED (allowed)
- Prevents false negative results for unimplemented features 