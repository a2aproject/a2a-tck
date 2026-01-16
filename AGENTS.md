# AGENTS.md - A2A Protocol TCK Project Guide for AI Agents

## Project Overview

**Project Name**: A2A Protocol Technology Compatibility Kit (TCK)  
**Version**: 1.0.0  
**Purpose**: Comprehensive validation framework for A2A (Agent-to-Agent) Protocol implementations
**Language**: Python 3.8+  
**License**: MIT

### What This Project Does

The A2A TCK is a sophisticated test suite that validates whether an A2A protocol implementation complies with the A2A v1.0.0 specification. It provides:

1. **Categorized Testing**: Clear separation of mandatory vs. optional requirements
2. **Multi-Transport Support**: Tests JSON-RPC, gRPC, and REST transports
3. **Capability-Based Validation**: Smart test execution based on Agent Card declarations
4. **Compliance Scoring**: Four-tier compliance levels with detailed reporting
5. **Progressive Enhancement**: Helps implementations improve from basic to full compliance

### Key Terminology

- **SUT (System Under Test)**: The A2A implementation being validated
- **Agent Card**: JSON document describing agent capabilities (`.well-known/agent.json`)
- **Transport**: Communication protocol (JSON-RPC 2.0, gRPC, HTTP+JSON/REST)
- **Compliance Level**: NON_COMPLIANT → MANDATORY → RECOMMENDED → FULL_FEATURED

## Project Architecture

### Directory Structure

```
a2a-tck/
├── tck/                          # Core TCK framework
│   ├── config.py                 # Global configuration & transport settings
│   ├── sut_client.py            # High-level SUT client interface
│   ├── agent_card_utils.py      # Agent Card parsing & validation
│   ├── message_utils.py         # Message construction utilities
│   ├── logging_config.py        # Logging configuration
│   └── transport/               # Transport layer implementations
│       ├── base_client.py       # Abstract transport interface
│       ├── jsonrpc_client.py    # JSON-RPC 2.0 over HTTP
│       ├── grpc_client.py       # gRPC transport
│       ├── rest_client.py       # HTTP+JSON/REST transport
│       └── transport_manager.py # Transport selection & management
│
├── tests/                        # Test suites
│   ├── mandatory/               # MUST pass for A2A compliance
│   │   ├── jsonrpc/            # JSON-RPC 2.0 compliance
│   │   ├── protocol/           # A2A protocol core methods
│   │   ├── security/           # Security requirements
│   │   └── transport/          # Transport-specific tests
│   ├── optional/                # Conditional & informational tests
│   │   ├── capabilities/       # Capability-based tests
│   │   ├── multi_transport/    # Transport equivalence
│   │   ├── quality/            # Production readiness
│   │   └── features/           # Optional features
│   ├── validators/              # Compliance validators
│   └── utils/                   # Test utilities
│
├── spec_tracker/                 # Specification tracking & analysis
│   ├── spec_downloader.py       # Download A2A spec from GitHub
│   ├── spec_parser.py           # Parse specification structure
│   ├── test_analyzer.py         # Analyze test coverage
│   └── report_generator.py      # Generate impact reports
│
├── util_scripts/                 # Utility scripts
│   ├── check_spec_changes.py    # Check for spec updates
│   ├── update_current_spec.py   # Update baseline spec
│   └── generate_compliance_report.py
│
├── docs/                         # Documentation
│   ├── SUT_REQUIREMENTS.md      # Requirements for SUTs
│   ├── SDK_VALIDATION_GUIDE.md  # SDK developer guide
│   ├── SPEC_UPDATE_WORKFLOW.md  # Spec update process
│   └── adrs/                    # Architecture Decision Records
│
├── run_tck.py                    # Main test runner CLI
├── run_sut.py                    # SUT management utility
├── pyproject.toml               # Project configuration
└── README.md                     # User documentation
```

## Core Components

### 1. Test Runner (`run_tck.py`)

**Purpose**: Main CLI interface for running TCK tests  
**Key Features**:
- Category-based test execution
- Multi-transport configuration
- Compliance report generation
- Verbose logging options

**Usage Patterns**:
```bash
# Basic compliance check
./run_tck.py --sut-url http://localhost:9999 --category mandatory

# Multi-transport testing
./run_tck.py --sut-url URL --transports jsonrpc,grpc --category all

# Generate compliance report
./run_tck.py --sut-url URL --category all --compliance-report report.json
```

### 2. Configuration System (`tck/config.py`)

**Purpose**: Centralized configuration management  
**Key Functions**:
- `set_config()`: Set SUT URL and test scope
- `get_sut_url()`: Retrieve configured SUT URL
- `set_auth_headers()`: Configure authentication
- `set_transport_selection_strategy()`: Configure transport selection
- `get_transport_specific_config()`: Get transport-specific settings

**Environment Variables**:
- `SUT_URL`: SUT base URL
- `TCK_STREAMING_TIMEOUT`: Streaming test timeout (default: 2.0s)
- `A2A_AUTH_TYPE`: Authentication type (bearer, basic, apikey, custom)
- `A2A_TRANSPORT_STRATEGY`: Transport selection strategy
- `A2A_REQUIRED_TRANSPORTS`: Comma-separated required transports

### 3. Transport Layer (`tck/transport/`)

**Architecture**: Abstract base class with concrete implementations

**Base Interface** (`base_client.py`):
```python
class BaseTransportClient(ABC):
    @abstractmethod
    async def send_message(self, method: str, params: dict) -> dict
    @abstractmethod
    async def stream_messages(self, method: str, params: dict) -> AsyncIterator
    @abstractmethod
    async def close(self)
```

**Implementations**:
- `JSONRPCClient`: JSON-RPC 2.0 over HTTP (backward compatible)
- `GRPCClient`: gRPC with Protocol Buffers
- `RESTClient`: HTTP+JSON/REST transport

**Transport Manager** (`transport_manager.py`):
- Parses Agent Card to discover available transports
- Selects appropriate transport based on strategy
- Manages transport lifecycle

### 4. SUT Client (`tck/sut_client.py`)

**Purpose**: High-level interface for interacting with SUT  
**Key Methods**:
- `send_message()`: Send A2A message
- `get_task()`: Retrieve task status
- `cancel_task()`: Cancel running task
- `stream_messages()`: Stream messages (SSE)
- `resubscribe_to_task()`: Resubscribe to task stream

**Usage Pattern**:
```python
async with SUTClient(sut_url) as client:
    response = await client.send_message(
        agent_id="test-agent",
        text="Hello",
        message_id="msg-123"
    )
```

### 5. Agent Card Utilities (`tck/agent_card_utils.py`)

**Purpose**: Parse and validate Agent Card  
**Key Functions**:
- `fetch_agent_card()`: Fetch Agent Card from SUT
- `validate_agent_card()`: Validate against schema
- `get_capability()`: Check if capability is declared
- `get_transport_urls()`: Extract transport endpoints

## Test Categories

### 🔴 MANDATORY Tests (`tests/mandatory/`)

**Criteria**: MUST pass for A2A compliance  
**Impact**: Failure = NOT A2A compliant  
**Exit Code**: Non-zero on failure

**Subcategories**:
- `jsonrpc/`: JSON-RPC 2.0 protocol compliance
- `protocol/`: A2A core methods (SendMessage, GetTask, CancelTask)
- `security/`: TLS, authentication, certificate validation
- `transport/`: Transport-specific requirements

**Key Tests**:
- `test_json_rpc_compliance.py`: JSON-RPC 2.0 structure validation
- `test_message_send_method.py`: SendMessage method compliance
- `test_tasks_get_method.py`: GetTask method compliance
- `test_agent_card_mandatory.py`: Required Agent Card fields

### 🔄 CAPABILITY Tests (`tests/optional/capabilities/`)

**Criteria**: Conditional mandatory based on Agent Card  
**Logic**: Skip if not declared, mandatory if declared  
**Impact**: Failure = False advertising

**Key Tests**:
- `test_streaming_methods.py`: Streaming capability validation
- `test_push_notifications.py`: Push notification support
- `test_authentication_methods.py`: Declared auth methods

**Capability Detection Pattern**:
```python
@pytest.mark.optional_capability
async def test_streaming_support(sut_client, agent_card):
    """Test streaming capability if declared."""
    capabilities = agent_card.get("capabilities", {})

    # Scenario 1: Capability NOT declared → Skip test
    if not capabilities.get("streaming"):
        pytest.skip("Streaming capability not declared in Agent Card")

    # Scenario 2: Capability IS declared → Test becomes MANDATORY
    # Failure here means false advertising (compliance violation)
    try:
        async for message in sut_client.stream_messages(...):
            assert message is not None
            break  # At least one message received
    except NotImplementedError:
        # Scenario 3: Declared but not implemented → FAIL
        pytest.fail(
            "Agent Card declares streaming capability but implementation "
            "raises NotImplementedError - this is false advertising!"
        )
    except AttributeError as e:
        pytest.fail(
            f"Agent Card declares streaming but endpoint/method missing: {e}"
        )
```

**Key Principle**: Capability tests are **conditionally mandatory**, not truly optional. If you claim a capability in your Agent Card, you MUST implement it correctly or face compliance failure.

### 🚀 TRANSPORT EQUIVALENCE Tests (`tests/optional/multi_transport/`)

**Criteria**: Conditional mandatory if multiple transports declared  
**Purpose**: Validate functional equivalence across transports  
\1v1.0.0\2

**Key Tests**:
- `test_multi_transport_equivalence.py`: Cross-transport consistency
- Method mapping validation (e.g., `message/send` → `SendMessage` gRPC)
- Error code consistency across transports

### 🛡️ QUALITY Tests (`tests/optional/quality/`)

**Criteria**: ALWAYS optional (never blocks compliance)  
**Purpose**: Production readiness assessment  
**Exit Code**: Zero (unless `--quality-required` flag)

**Key Tests**:
- Concurrent request handling
- Unicode/special character support
- Edge case robustness
- Error recovery

### 🎨 FEATURE Tests (`tests/optional/features/`)

**Criteria**: ALWAYS optional and informational  
**Purpose**: Optional feature completeness  
**Exit Code**: Zero (unless `--features-required` flag)

## Development Patterns

### 1. Test Markers

Tests use pytest markers for categorization:

```python
@pytest.mark.mandatory
@pytest.mark.mandatory_protocol
def test_send_message_basic():
    """Test basic SendMessage functionality."""
    pass

@pytest.mark.optional_capability
def test_streaming_when_declared():
    """Test streaming if capability declared."""
    pass
```

**Available Markers**:
- `mandatory`: Blocks SDK compliance
- `mandatory_jsonrpc`: JSON-RPC 2.0 compliance
- `mandatory_protocol`: A2A protocol requirements
- `optional_capability`: Capability-dependent
- `quality_production`: Production readiness
- `transport_equivalence`: Multi-transport equivalence
- `a2a_v100`: A2A v1.0.0\2

### 2. Specification References

All tests include specification references:

```python
def test_message_send_method():
    """
    Test SendMessage method compliance.
    
    Specification Reference:
\1v1.0.0\2
        
    Requirements:
        - MUST accept agentId, text, messageId parameters
        - MUST return taskId in response
        - MUST validate message structure
    """
```

### 3. Capability-Based Testing

```python
@pytest.mark.optional_capability
async def test_streaming_support(sut_client, agent_card):
    """Test streaming capability if declared."""
    capabilities = agent_card.get("capabilities", {})
    
    if not capabilities.get("streaming"):
        pytest.skip("Streaming capability not declared")
    
    # Test becomes mandatory since capability is declared
    async for message in sut_client.stream_messages(...):
        assert message is not None
```

### 4. Transport-Agnostic Testing

```python
async def test_send_message_all_transports(transport_client):
    """Test SendMessage across all available transports."""
    # transport_client is automatically selected based on strategy
    response = await transport_client.send_message(
        method="message/send",
        params={"agentId": "test", "text": "Hello"}
    )
    assert "taskId" in response
```

## Compliance Scoring

### Compliance Levels

1. **NON_COMPLIANT** (🔴)
   - Any mandatory test failure
   - Cannot be used for A2A integrations

2. **MANDATORY** (🟡)
   - 100% mandatory test pass rate
   - Basic A2A integration support
   - Suitable for development/testing

3. **RECOMMENDED** (🟢)
   - Mandatory: 100%
   - Capability: ≥85%
   - Quality: ≥75%
   - Production-ready with confidence

4. **FULL_FEATURED** (🏆)
   - Capability: ≥95%
   - Quality: ≥90%
   - Feature: ≥80%
   - Complete A2A implementation

### Scoring Algorithm

```python
def calculate_compliance_level(scores: Dict[str, float]) -> str:
    if scores["mandatory"] < 100.0:
        return "NON_COMPLIANT"
    
    if scores["capability"] >= 95 and scores["quality"] >= 90 and scores["feature"] >= 80:
        return "FULL_FEATURED"
    
    if scores["capability"] >= 85 and scores["quality"] >= 75:
        return "RECOMMENDED"
    
    return "MANDATORY"
```

## Common Tasks for AI Agents

### Task 1: Add a New Test

1. **Determine Category**: Is it mandatory, capability-based, quality, or feature?
2. **Choose Location**: Place in appropriate `tests/` subdirectory
3. **Add Markers**: Use correct pytest markers
4. **Include Spec Reference**: Document specification section
5. **Follow Patterns**: Use existing tests as templates

**Example**:
```python
# tests/mandatory/protocol/test_new_method.py
import pytest

@pytest.mark.mandatory
@pytest.mark.mandatory_protocol
async def test_new_method_compliance(sut_client):
    """
    Test NewMethod compliance.
    
    Specification Reference:
\1v1.0.0\2
        
    Requirements:
        - MUST accept required parameters
        - MUST return expected response structure
    """
    response = await sut_client.new_method(param="value")
    assert "expectedField" in response
```

### Task 2: Update Specification Tracking

When A2A specification changes:

1. **Check Changes**: `python util_scripts/check_spec_changes.py`
2. **Review Impact**: Examine generated report in `reports/`
\1v1.0.1\2
4. **Update Tests**: Modify affected tests based on spec changes

### Task 3: Add Transport Support

To add a new transport type:

1. **Create Client**: Implement `BaseTransportClient` in `tck/transport/`
2. **Add Transport Type**: Update `TransportType` enum in `base_client.py`
3. **Update Manager**: Add transport detection in `transport_manager.py`
4. **Add Tests**: Create transport-specific tests in `tests/mandatory/transport/`

### Task 4: Debug Test Failures

**Verbose Mode**:
```bash
./run_tck.py --sut-url URL --category mandatory --verbose
```

**Single Test**:
```bash
python -m pytest tests/mandatory/protocol/test_message_send_method.py::test_basic \
    --sut-url URL -s -v --log-cli-level=DEBUG
```

**Check Logs**:
- Test output shows detailed request/response
- Use `--verbose` flag for full logging
- Check `reports/` directory for generated reports

## Key Files Reference

### Configuration & Setup
- `pyproject.toml`: Project dependencies and metadata
- `.env.example`: Environment variable template
- `requirements.txt`: Python dependencies

### Core Framework
- `tck/config.py`: Global configuration (200+ lines)
- `tck/sut_client.py`: High-level SUT interface (400+ lines)
- `tck/transport/transport_manager.py`: Transport selection logic (300+ lines)

### Test Infrastructure
- `tests/conftest.py`: Pytest fixtures and configuration
- `tests/markers.py`: Test marker definitions
- `tests/validators/`: Compliance validators

### Documentation
- `README.md`: User-facing documentation
- `docs/SUT_REQUIREMENTS.md`: Requirements for SUTs
- `docs/SDK_VALIDATION_GUIDE.md`: SDK developer guide
- `docs/SPEC_UPDATE_WORKFLOW.md`: Specification update process

### Utilities
- `run_tck.py`: Main test runner
- `run_sut.py`: SUT management utility
- `util_scripts/check_spec_changes.py`: Spec change detection

## Environment Variables

### Core Configuration
- `SUT_URL`: Base URL of SUT
- `TCK_STREAMING_TIMEOUT`: Streaming timeout in seconds (default: 2.0)

### Authentication
- `A2A_AUTH_TYPE`: bearer, basic, apikey, custom
- `A2A_AUTH_TOKEN`: Authentication token/credential
- `A2A_AUTH_HEADER`: Custom header name (for apikey/custom)
- `A2A_AUTH_USERNAME`: Username (for basic auth)
- `A2A_AUTH_PASSWORD`: Password (for basic auth)
- `A2A_AUTH_HEADERS`: JSON object with custom headers

### Transport Configuration
- `A2A_TRANSPORT_STRATEGY`: agent_preferred, prefer_jsonrpc, prefer_grpc, prefer_rest, all_supported
- `A2A_PREFERRED_TRANSPORT`: jsonrpc, grpc, rest
- `A2A_REQUIRED_TRANSPORTS`: Comma-separated list (strict mode)
- `A2A_DISABLED_TRANSPORTS`: Comma-separated list
- `A2A_ENABLE_EQUIVALENCE_TESTING`: true/false (default: true)

### Transport-Specific
- `A2A_JSONRPC_*`: JSON-RPC specific config (e.g., `A2A_JSONRPC_TIMEOUT`)
- `A2A_GRPC_*`: gRPC specific config (e.g., `A2A_GRPC_MAX_MESSAGE_SIZE`)
- `A2A_REST_*`: REST specific config (e.g., `A2A_REST_TIMEOUT`)

### Strict Mode
- `A2A_TCK_FAIL_ON_QUALITY`: Treat quality tests as required (1/true/yes)
- `A2A_TCK_FAIL_ON_FEATURES`: Treat feature tests as required (1/true/yes)

## Best Practices for AI Agents

### When Adding Tests
1. ✅ Always include specification references
2. ✅ Use appropriate pytest markers
3. ✅ Follow existing test patterns
4. ✅ Add docstrings with clear requirements
5. ✅ Consider capability-based logic
6. ✅ Test across all relevant transports

### When Modifying Code
1. ✅ Maintain backward compatibility
2. ✅ Update documentation (README.md, AGENTS.md)
3. ✅ Run full test suite before committing
4. ✅ Follow Python type hints conventions
5. ✅ Use async/await for I/O operations

### When Debugging
1. ✅ Use verbose mode for detailed output
2. ✅ Check Agent Card for capability declarations
3. ✅ Verify transport configuration
4. ✅ Review specification references
5. ✅ Test with single transport first

### When Updating Specifications
1. ✅ Use `check_spec_changes.py` to detect changes
2. ✅ Review impact report carefully
3. ✅ Update affected tests systematically
4. ✅ Update documentation to reflect changes
5. ✅ Run full test suite to verify updates

## Coding Guidelines

### Python Style & Conventions

**Code Formatting**:
- **Line Length**: Maximum 100 characters (configured in `pyproject.toml`)
- **Formatter**: Black (run with `black .`)
- **Import Sorting**: isort with Black profile (run with `isort .`)
- **Type Hints**: Use Python type hints for all function signatures
- **Python Version**: Target Python 3.8+ compatibility

**Example**:
```python
from typing import Optional, Dict, List
import asyncio

async def fetch_agent_card(
    sut_url: str,
    timeout: float = 30.0,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, any]:
    """
    Fetch Agent Card from SUT.
    
    Args:
        sut_url: Base URL of the SUT
        timeout: Request timeout in seconds
        headers: Optional HTTP headers
        
    Returns:
        Parsed Agent Card as dictionary
        
    Raises:
        ValueError: If Agent Card is invalid
        httpx.HTTPError: If request fails
    """
    # Implementation here
    pass
```

### Naming Conventions

**Files & Modules**:
- Test files: `test_<feature>.py` (e.g., `test_message_send_method.py`)
- Module files: `snake_case.py` (e.g., `agent_card_utils.py`)
- Avoid abbreviations unless widely understood (e.g., `sut`, `tck`, `grpc`)

**Functions & Variables**:
- Functions: `snake_case` (e.g., `get_agent_card()`, `validate_response()`)
- Variables: `snake_case` (e.g., `agent_card`, `task_id`, `response_data`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TIMEOUT`, `MAX_RETRIES`)
- Private functions/methods: Prefix with `_` (e.g., `_parse_transport()`)

**Classes**:
- Class names: `PascalCase` (e.g., `SUTClient`, `TransportManager`, `BaseTransportClient`)
- Exception classes: Suffix with `Error` (e.g., `ValidationError`, `TransportError`)

### Async/Await Patterns

**Always use async/await for I/O operations**:
```python
# ✅ GOOD - Async I/O
async def send_request(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        return response.json()

# ❌ BAD - Blocking I/O in async context
async def send_request(url: str) -> dict:
    response = requests.post(url, json=data)  # Blocks event loop!
    return response.json()
```

**Context Managers**:
```python
# ✅ GOOD - Proper resource cleanup
async with SUTClient(sut_url) as client:
    response = await client.send_message(...)
    # Client automatically closed

# ❌ BAD - Manual cleanup required
client = SUTClient(sut_url)
response = await client.send_message(...)
await client.close()  # Easy to forget!
```

### Error Handling

**Be Specific with Exceptions**:
```python
# ✅ GOOD - Specific exception handling
try:
    agent_card = await fetch_agent_card(sut_url)
except httpx.HTTPStatusError as e:
    logger.error(f"HTTP error fetching Agent Card: {e.response.status_code}")
    raise
except httpx.TimeoutException:
    logger.error("Timeout fetching Agent Card")
    raise
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON in Agent Card: {e}")
    raise ValueError("Agent Card is not valid JSON")

# ❌ BAD - Catching everything
try:
    agent_card = await fetch_agent_card(sut_url)
except Exception as e:
    logger.error(f"Error: {e}")
    raise
```

**Provide Context in Error Messages**:
```python
# ✅ GOOD - Detailed error context
if "taskId" not in response:
    raise ValueError(
        f"Response missing required 'taskId' field. "
        f"Response keys: {list(response.keys())}"
    )

# ❌ BAD - Vague error message
if "taskId" not in response:
    raise ValueError("Invalid response")
```

### Logging Best Practices

**Use Appropriate Log Levels**:
```python
import logging

logger = logging.getLogger(__name__)

# DEBUG - Detailed diagnostic information
logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")

# INFO - General informational messages
logger.info(f"Testing transport: {transport_type.value}")

# WARNING - Unexpected but recoverable situations
logger.warning(f"Capability '{capability}' declared but not tested")

# ERROR - Error conditions that don't stop execution
logger.error(f"Failed to validate response: {error}")

# CRITICAL - Serious errors requiring immediate attention
logger.critical(f"Cannot connect to SUT at {sut_url}")
```

**Structured Logging**:
```python
# ✅ GOOD - Structured, parseable logs
logger.info(
    "Test completed",
    extra={
        "test_name": "test_send_message",
        "transport": "jsonrpc",
        "duration_ms": 150,
        "status": "passed"
    }
)

# ❌ BAD - Unstructured string concatenation
logger.info(f"Test test_send_message on jsonrpc took 150ms and passed")
```

### Test Writing Guidelines

**Test Structure (AAA Pattern)**:
```python
@pytest.mark.mandatory
@pytest.mark.mandatory_protocol
async def test_send_message_basic(sut_client):
    """
    Test basic SendMessage functionality.
    
    Specification Reference:
\1v1.0.0\2
    """
    # ARRANGE - Setup test data
    agent_id = "test-agent"
    message_text = "Hello, World!"
    message_id = f"test-msg-{uuid.uuid4()}"
    
    # ACT - Execute the operation
    response = await sut_client.send_message(
        agent_id=agent_id,
        text=message_text,
        message_id=message_id
    )
    
    # ASSERT - Verify the results
    assert "taskId" in response, "Response must contain taskId"
    assert isinstance(response["taskId"], str), "taskId must be a string"
    assert len(response["taskId"]) > 0, "taskId must not be empty"
```

**Test Naming**:
- Pattern: `test_<feature>_<scenario>` (e.g., `test_send_message_with_invalid_agent_id`)
- Be descriptive: Test name should explain what is being tested
- Use underscores for readability

**Fixtures**:

The TCK provides two main client fixtures with different abstraction levels:

```python
# conftest.py - Shared fixtures

@pytest.fixture
async def sut_client():
    """
    High-level SUT client with convenience methods.

    Use this when:
    - Testing A2A protocol methods (SendMessage, GetTask, CancelTask)
    - You want human-friendly method names
    - Transport details don't matter for your test

    Example:
        response = await sut_client.send_message(
            agent_id="test",
            text="Hello",
            message_id="msg-123"
        )
    """
    client = SUTClient(get_sut_url())
    yield client
    await client.close()

@pytest.fixture
async def transport_client():
    """
    Low-level transport client for transport-specific testing.

    Use this when:
    - Testing transport equivalence (JSON-RPC, gRPC, REST)
    - Testing JSON-RPC 2.0 compliance specifically
    - You need to test raw transport behavior
    - Testing method name mapping across transports

    Example:
        response = await transport_client.send_message(
            method="message/send",  # JSON-RPC method name
            params={"agentId": "test", "text": "Hello"}
        )

    Note: transport_client is selected based on strategy configuration.
    It directly uses BaseTransportClient implementations.
    """
    # Actual fixture implementation in tests/conftest.py
    pass

@pytest.fixture
def agent_card():
    """Provide Agent Card for tests."""
    return fetch_agent_card(get_sut_url())
```

**Relationship**:
- `sut_client` **wraps** `transport_client` internally
- `sut_client` provides convenience methods like `send_message()`, `get_task()`
- `transport_client` exposes raw `send_message(method, params)` for transport testing
- Both use the same underlying transport layer, but at different abstraction levels

**When to use each**:
```python
# ✅ Use sut_client for A2A protocol tests
async def test_send_message_compliance(sut_client):
    response = await sut_client.send_message(agent_id="test", text="Hi")
    assert "taskId" in response

# ✅ Use transport_client for transport-specific tests
async def test_jsonrpc_method_mapping(transport_client):
    response = await transport_client.send_message(
        method="message/send",  # Explicit JSON-RPC method
        params={"agentId": "test", "text": "Hi"}
    )
    assert "result" in response  # JSON-RPC structure
```

### Documentation Standards

**Docstring Format (Google Style)**:
```python
def calculate_compliance_score(
    mandatory_pass: int,
    mandatory_total: int,
    capability_pass: int,
    capability_total: int
) -> float:
    """
    Calculate weighted compliance score.
    
    The compliance score is calculated using weighted averages where
    mandatory tests have higher weight than capability tests.
    
    Args:
        mandatory_pass: Number of passed mandatory tests
        mandatory_total: Total number of mandatory tests
        capability_pass: Number of passed capability tests
        capability_total: Total number of capability tests
        
    Returns:
        Compliance score as percentage (0.0 to 100.0)
        
    Raises:
        ValueError: If total counts are zero or negative
        
    Example:
        >>> calculate_compliance_score(10, 10, 8, 10)
        92.0
    """
    if mandatory_total <= 0 or capability_total <= 0:
        raise ValueError("Total counts must be positive")
    
    mandatory_score = (mandatory_pass / mandatory_total) * 100
    capability_score = (capability_pass / capability_total) * 100
    
    # Weighted average: 70% mandatory, 30% capability
    return (mandatory_score * 0.7) + (capability_score * 0.3)
```

**Module Docstrings**:
```python
"""
\1v1.0.0

This module provides transport selection and management functionality
for multi-transport testing scenarios. It handles:
- Agent Card parsing for transport discovery
- Transport selection based on strategy
- Transport lifecycle management

\1v1.0.0\2
"""
```

### Code Organization

**Import Order** (enforced by isort):
1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# Standard library
import asyncio
import json
from typing import Optional, Dict, List

# Third-party
import pytest
import httpx
from jsonschema import validate

# Local
from tck.config import get_sut_url
from tck.transport.base_client import BaseTransportClient
from tck.agent_card_utils import fetch_agent_card
```

**Function Length**:
- Keep functions focused and under 50 lines when possible
- Extract complex logic into helper functions
- Use descriptive names for extracted functions

**File Length**:
- Keep modules under 500 lines when possible
- Split large modules into logical submodules
- Use `__init__.py` to expose public API

### Performance Considerations

**Avoid Blocking Operations**:
```python
# ✅ GOOD - Non-blocking sleep
await asyncio.sleep(1.0)

# ❌ BAD - Blocks event loop
import time
time.sleep(1.0)
```

**Efficient Data Structures**:
```python
# ✅ GOOD - Set for membership testing
valid_transports = {"jsonrpc", "grpc", "rest"}
if transport in valid_transports:
    ...

# ❌ BAD - List for membership testing (O(n))
valid_transports = ["jsonrpc", "grpc", "rest"]
if transport in valid_transports:  # Slower for large lists
    ...
```

**Resource Cleanup**:
```python
# ✅ GOOD - Explicit cleanup with context manager
async with httpx.AsyncClient() as client:
    response = await client.get(url)

# ✅ GOOD - Manual cleanup with try/finally
client = httpx.AsyncClient()
try:
    response = await client.get(url)
finally:
    await client.aclose()
```

### Security Best Practices

**Never Log Sensitive Data**:
```python
# ✅ GOOD - Redact sensitive information
logger.info(f"Authentication header: Bearer ***REDACTED***")

# ❌ BAD - Logging credentials
logger.info(f"Authentication header: {auth_header}")
```

**Validate Input**:
```python
# ✅ GOOD - Input validation
def set_timeout(timeout: float) -> None:
    if timeout <= 0:
        raise ValueError("Timeout must be positive")
    if timeout > 300:
        raise ValueError("Timeout cannot exceed 300 seconds")
    _timeout = timeout

# ❌ BAD - No validation
def set_timeout(timeout: float) -> None:
    _timeout = timeout
```

### Git Commit Guidelines

**Commit Message Format** (Conventional Commits):
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions or modifications
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks

**Examples**:
```
feat(transport): add REST transport support

\1v1.0.0
specification. Includes method mapping and error handling.

Closes #123

---

fix(tests): correct streaming timeout calculation

The streaming timeout was using wrong multiplier causing
false negatives in slow network conditions.

---

docs(readme): update multi-transport testing examples

Add examples for gRPC and REST transport testing with
various configuration options.
```

### Code Review Checklist

Before submitting code, verify:

- [ ] All tests pass locally
- [ ] Code follows style guidelines (Black, isort)
- [ ] Type hints are present and correct
- [ ] Docstrings are complete and accurate
- [ ] No sensitive data in logs or code
- [ ] Error handling is appropriate
- [ ] Async/await used correctly
- [ ] Resources are properly cleaned up
- [ ] Specification references are included (for tests)
- [ ] Documentation updated (if needed)
- [ ] Commit messages follow conventions

## Project Dependencies

### Core Dependencies
- `pytest>=7.0.0`: Test framework
- `pytest-asyncio>=0.20.0`: Async test support
- `httpx>=0.24.0`: HTTP client
- `requests>=2.31.0`: HTTP library
- `jsonschema>=4.20.0`: JSON schema validation

\1v1.0.0\2
- `grpcio>=1.62.0`: gRPC support
- `grpcio-tools>=1.62.0`: gRPC code generation
- `protobuf>=4.25.0`: Protocol Buffers

### Security & TLS
- `pyOpenSSL>=23.0.0`: Certificate analysis

### Configuration
- `PyYAML>=5.0.0`: YAML parsing
- `python-dotenv>=1.0.0`: Environment variable management

### Testing & Reporting
- `pytest-json-report>=1.5.0`: JSON test reports
- `deepdiff>=6.7.1`: Deep comparison utilities

## Quick Reference Commands

```bash
# Basic compliance check
./run_tck.py --sut-url http://localhost:9999 --category mandatory

# Full validation with report
./run_tck.py --sut-url URL --category all --compliance-report report.json

# Multi-transport testing
./run_tck.py --sut-url URL --transports jsonrpc,grpc --category all

# Verbose debugging
./run_tck.py --sut-url URL --category mandatory --verbose

# Single test debugging
python -m pytest tests/path/to/test.py::test_name --sut-url URL -s -v

# Check spec changes
python util_scripts/check_spec_changes.py

\1v1.0.1

# Strict mode (internal projects)
./run_tck.py --sut-url URL --category all --quality-required --features-required
```

## Support & Resources

\1v1.0.0\2
- **Documentation**: `docs/` directory
- **Examples**: `python-sut/` directory (reference implementation)
- **Issue Tracking**: GitHub Issues
- **Architecture Decisions**: `docs/adrs/` directory

---

**Last Updated**: 2026-01-16  
**A2A TCK Version**: 1.0.0  
**Target Specification**: A2A Protocol v1.0.0
