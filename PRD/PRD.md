# A2A TCK v1.0 - Product Requirements Document

## Document Information

| Field | Value |
|-------|-------|
| Version | 1.0-draft |
| Last Updated | 2025-01-27 |
| Target Audience | Junior Developer |
| Specification Reference | [A2A Protocol v1.0](https://github.com/a2aproject/A2A/blob/main/docs/specification.md) |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Goals and Non-Goals](#2-goals-and-non-goals)
3. [Background and Context](#3-background-and-context)
4. [Architecture Overview](#4-architecture-overview)
5. [Detailed Design](#5-detailed-design)
6. [Implementation Phases](#6-implementation-phases)
7. [Testing Strategy](#7-testing-strategy)
8. [Appendices](#8-appendices)

---

## 1. Executive Summary

### 1.1 Purpose

The A2A TCK (Technology Compatibility Kit) is a comprehensive test suite that validates implementations of the **A2A (Agent-to-Agent) Protocol v1.0**. It ensures that A2A server implementations correctly handle all protocol operations across three transport bindings: **gRPC**, **JSON-RPC**, and **HTTP+JSON**.

### 1.2 Key Design Decisions

1. **Proto as Source of Truth**: The canonical data model is defined in `a2a.proto`. All validation references this definition.

2. **Transport-Native Testing**: Each transport is tested using its native response format. No cross-transport conversion.

3. **JSON Schema for Validation**: JSON-RPC and REST responses are validated against the official `a2a.json` schema (derived from `a2a.proto`).

4. **Single Requirement, Multiple Validators**: Each specification requirement has one logical test that runs across all transports via pytest parametrization.

5. **Transport-Specific Corner Cases**: Error handling, streaming, and async behaviors have dedicated transport-specific tests.

### 1.3 Success Criteria

- 100% coverage of MUST requirements from the specification
- Clear compliance reporting per-requirement AND per-transport
- Transport-native validation with zero cross-format conversion errors
- Easy traceability from test to specification section

---

## 2. Goals and Non-Goals

### 2.1 Goals

| ID | Goal | Priority |
|----|------|----------|
| G1 | Validate A2A v1.0 specification compliance | P0 |
| G2 | Support all three transports (gRPC, JSON-RPC, REST) | P0 |
| G3 | Generate machine-readable compliance reports | P0 |
| G4 | Clear test-to-spec traceability | P0 |
| G5 | Extensible architecture for future spec versions | P1 |
| G6 | Developer-friendly error messages | P1 |

### 2.2 Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG1 | Backward compatibility with v0.3 | Clean break to v1.0 |
| NG2 | Performance benchmarking | Focus is correctness, not speed |
| NG3 | Client SDK validation | TCK tests servers, not clients |
| NG4 | Security penetration testing | Out of scope for compliance |

---

## 3. Background and Context

### 3.1 A2A Protocol v1.0 Structure

The specification uses a three-layer architecture:

```
Layer 1: Canonical Data Model (a2a.proto)
    │     └── Single authoritative normative definition
    │
Layer 2: Abstract Operations
    │     └── Binding-independent capabilities and behaviors
    │
Layer 3: Protocol Bindings
          ├── JSON-RPC (Section 9)
          ├── gRPC (Section 10)
          └── HTTP+JSON (Section 11)
```

**Key Principle**: All bindings guarantee "functional equivalence" for core semantics while varying transport mechanics.

### 3.2 Specification Artifacts

| Artifact | Location | Purpose |
|----------|----------|---------|
| `a2a.proto` | `specification/grpc/a2a.proto` | Canonical message definitions |
| `a2a.json` | `specification/json/a2a.json` | JSON Schema (derived from proto) |
| `specification.md` | `specification/specification.md` | Full specification with requirements |

### 3.3 Core Protocol Objects

From `a2a.proto` (see [Specification Section 4](https://github.com/a2aproject/A2A/blob/main/docs/specification.md)
and [a2a.proto](https://github.com/a2aproject/A2A/blob/main/specification/grpc/a2a.proto)):

| Object | Description | Key Fields |
|--------|-------------|------------|
| **Task** | Stateful work unit | `id`, `context_id`, `status`, `artifacts`, `history` |
| **Message** | Communication turn | `message_id`, `role`, `parts`, `metadata` |
| **Part** | Content unit (oneof) | `text` \| `file` \| `data` |
| **Artifact** | Agent-generated output | `artifact_id`, `name`, `parts` |
| **AgentCard** | Agent metadata | `name`, `capabilities`, `skills`, `security_schemes` |

### 3.4 Transport Bindings Summary

| Aspect | gRPC | JSON-RPC | REST |
|--------|------|----------|------|
| **Method Invocation** | RPC service | `method` field | HTTP verb + path |
| **Serialization** | Protobuf binary | JSON | JSON |
| **Streaming** | Native gRPC stream | SSE | SSE |
| **Error Format** | gRPC status codes | JSON-RPC error object | HTTP status + Problem Details |
| **Spec Section** | Section 10 | Section 9 | Section 11 |

Section 5 also defines Protocol Binding Requirements and Interoperability (including method and error code mappings)

### 3.5 Requirement Levels (RFC 2119)

| Keyword | Meaning | TCK Treatment |
|---------|---------|---------------|
| **MUST** | Absolute requirement | Test failure = non-compliant |
| **SHOULD** | Strong recommendation | Test failure = warning |
| **MAY** | Optional behavior | Test if capability declared |

Some capabilities provided by the remote agents are optional. However if the
capabilities are enabled, their requirements are absolute.
Such tests should be skipped if the remote agents to do not provide the capabilities.

---

## 4. Architecture Overview

### 4.1 High-Level Architecture

See: [architecture.mmd](./architecture.mmd)

```
┌─────────────────────────────────────────────────────────────┐
│                    A2A Specification                        │
│              (a2a.proto, spec.md)                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    derived specification                    │
│                       (a2a.json)                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  Requirement Layer                          │
│         (Requirement definitions with spec references)      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  Validation Layer                           │
│    ┌─────────────────────┴─────────────────────┐            │
│    │  JSON Schema Validator  │  Proto Validator│            │
│    │    (jsonrpc, rest)      │     (grpc)      │            │
│    └───────────────────────────────────────────┘            │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Transport Layer                           │
│         (gRPC client, JSON-RPC client, REST client)         │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                     Test Layer                              │
│    ┌────────────────────────────────────────────────┐       │
│    │  Core Tests (parametrized)  │  Corner Cases    │       │
│    │     ~100 requirements       │  per transport   │       │
│    └────────────────────────────────────────────────┘       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Reporting Layer                           │
│       (Compliance reports: JSON, HTML, Console)             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Directory Structure

```
a2a-tck/
├── pyproject.toml              # Project configuration
├── run_tck.py                  # CLI entry point
│
├── specification/              # Local copy of spec artifacts
│   ├── a2a.proto              # Canonical proto (synced from A2A repo)
│   ├── a2a.json               # JSON Schema (derived from a2a.proto)
│   ├── specification.md       # Specification (synced from A2A repo)
│   └── generated/             # Generated Python code
│       └── a2a_pb2.py         # Proto-generated Python classes
│
├── tck/                        # Core library
│   ├── __init__.py
│   ├── config.py              # Global configuration
│   │
│   ├── requirements/          # Requirement definitions
│   │   ├── __init__.py
│   │   ├── base.py           # RequirementSpec base class
│   │   ├── registry.py       # ALL_REQUIREMENTS collection
│   │   ├── core_operations.py # Core Operations
│   │   ├── data_model.py     # Data Model
│   │   ├── card_discovery.py # Agent card discovery
│   │   ├── auth.py           # Authn and authz
│   │   └── ...               # Other sections
│   │
│   ├── validators/            # Validation logic
│   │   ├── __init__.py
│   │   ├── json_schema.py    # JSON Schema validation
│   │   ├── proto_schema.py   # Proto descriptor validation
│   │   ├── grpc/             # gRPC-specific validators
│   │   ├── jsonrpc/          # JSON-RPC-specific validators
│   │   └── rest/             # REST-specific validators
│   │
│   ├── transport/             # Transport clients
│   │   ├── __init__.py
│   │   ├── base.py           # Abstract base client
│   │   ├── grpc_client.py    # gRPC client
│   │   ├── jsonrpc_client.py # JSON-RPC client
│   │   ├── rest_client.py    # REST client
│   │   └── manager.py        # Transport orchestration
│   │
│   └── reporting/             # Compliance reporting
│       ├── __init__.py
│       ├── collector.py      # Test result collection
│       ├── aggregator.py     # Result aggregation
│       └── formatters.py     # JSON/HTML/Console output
│
├── tests/                      # Test suite
│   ├── conftest.py            # Pytest configuration & fixtures
│   ├── markers.py             # Custom pytest markers
│   │
│   ├── core_operations/          # Core requirement tests
│   │   └── test_requirements.py  # Parametrized tests
│   │
│   ├── grpc/                  # gRPC corner cases
│   │   ├── test_status_codes.py
│   │   └── test_streaming.py
│   │
│   ├── jsonrpc/               # JSON-RPC corner cases
│   │   ├── test_error_codes.py
│   │   └── test_sse_streaming.py
│   │
│   └── rest/                  # REST corner cases
│       ├── test_http_status.py
│       ├── test_problem_details.py
│       └── test_sse_streaming.py
│
└── reports/                    # Generated reports (gitignored)
    ├── compliance.json
    ├── junitreport.xml
    └── compliance.html
```

### 4.3 Key Design Patterns

#### 4.3.1 Validation Flow

See: [validation-flow.mmd](./validation-flow.mmd)

**Principle**: Each transport validates using its native format. No conversion between transports.

- **gRPC**: Response is proto message → validate against proto descriptor
- **JSON-RPC**: Response is JSON → unwrap envelope → validate against JSON Schema
- **HTTP+JSON**: Response is JSON → validate against JSON Schema

#### 4.3.2 Test Parametrization

See: [test-parametrization.mmd](./test-parametrization.mmd)

```python
# tests/core/test_requirements.py
@pytest.mark.parametrize("transport", ["grpc", "jsonrpc", "rest"])
@pytest.mark.parametrize("requirement", ALL_REQUIREMENTS, ids=lambda r: r.id)
def test_requirement(transport, requirement, transport_clients, validators):
    # Execute
    client = transport_clients[transport]
    response = client.execute(requirement.operation, requirement.sample_input)

    # Validate
    validator = validators[transport]
    result = validator.validate(response, requirement)

    # Assert
    assert result.valid, f"{requirement.id} failed: {result.errors}"
```

#### 4.3.3 Compliance Reporting

See: [compliance-report.mmd](./compliance-report.mmd)

**Two views**:
1. **Per-Requirement**: Did REQ-3.1 pass on all transports?
2. **Per-Transport**: How many requirements did gRPC pass?

---

## 5. Detailed Design

### 5.1 Requirement Layer

#### 5.1.1 RequirementSpec Base Class

```python
# tck/requirements/base.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class RequirementLevel(Enum):
    MUST = "MUST"
    SHOULD = "SHOULD"
    MAY = "MAY"

class OperationType(Enum):
    SEND_MESSAGE = "SendMessage"
    SEND_STREAMING_MESSAGE = "SendStreamingMessage"
    GET_TASK = "GetTask"
    LIST_TASKS = "ListTasks"
    CANCEL_TASK = "CancelTask"
    SUBSCRIBE_TO_TASK = "SubscribeToTask"
    # Push notification operations
    CREATE_PUSH_CONFIG = "CreateTaskPushNotificationConfig"
    GET_PUSH_CONFIG = "GetTaskPushNotificationConfig"
    LIST_PUSH_CONFIGS = "ListTaskPushNotificationConfig"
    DELETE_PUSH_CONFIG = "DeleteTaskPushNotificationConfig"
    # Agent card
    GET_EXTENDED_AGENT_CARD = "GetExtendedAgentCard"

@dataclass
class TransportBinding:
    """Transport-specific operation details."""
    grpc_rpc: str                    # e.g., "SendMessage"
    jsonrpc_method: str              # e.g., "SendMessage"
    http_json_method: str                 # e.g., "POST"
    http_json_path: str                   # e.g., "/message:send"

@dataclass
class RequirementSpec:
    """Defines a single specification requirement."""
    id: str                          # e.g., "REQ-3.1.1"
    section: str                     # e.g., "3.1.1"
    title: str                       # e.g., "Send Message Operation"
    level: RequirementLevel          # MUST, SHOULD, MAY
    description: str                 # Full requirement text
    operation: OperationType         # Which operation this tests
    binding: TransportBinding        # Transport-specific details

    # Validation references
    proto_request_type: str          # e.g., "SendMessageRequest"
    proto_response_type: str         # e.g., "SendMessageResponse"
    json_schema_ref: str             # e.g., "#/$defs/SendMessageResponse"

    # Test data
    sample_input: dict = field(default_factory=dict)
    expected_behavior: str = ""

    # Metadata
    spec_url: str = ""               # Link to spec section
    tags: list[str] = field(default_factory=list)
```

#### 5.1.2 Requirement Definition Example

```python
# tck/requirements/section_3.py
from tck.requirements.base import (
    RequirementSpec, RequirementLevel, OperationType, TransportBinding
)

REQ_3_1_1_SEND_MESSAGE = RequirementSpec(
    id="REQ-3.1.1",
    section="3.1.1",
    title="Send Message Operation",
    level=RequirementLevel.MUST,
    description=(
        "Agents MUST accept SendMessage requests and return a valid "
        "SendMessageResponse containing either a Task or Message."
    ),
    operation=OperationType.SEND_MESSAGE,
    binding=TransportBinding(
        grpc_rpc="SendMessage",
        jsonrpc_method="SendMessage",
        http_json_method="POST",
        http_json_path="/message:send",
    ),
    proto_request_type="SendMessageRequest",
    proto_response_type="SendMessageResponse",
    json_schema_ref="#/$defs/SendMessageResponse",
    sample_input={
        "message": {
            "role": "user",
            "parts": [{"text": "Hello, agent!"}]
        }
    },
    expected_behavior="Returns Task or Message with valid structure",
    spec_url="https://github.com/a2aproject/A2A/blob/main/docs/specification.md#311-send-message",
    tags=["core", "messaging"],
)
```

#### 5.1.3 Requirement Registry

```python
# tck/requirements/registry.py
from tck.requirements.section_3 import *
from tck.requirements.section_4 import *
# ... import all sections

ALL_REQUIREMENTS: list[RequirementSpec] = [
    # Section 3: Core Operations
    REQ_3_1_1_SEND_MESSAGE,
    REQ_3_1_2_SEND_STREAMING_MESSAGE,
    REQ_3_2_1_GET_TASK,
    # ... ~100 requirements
]

MUST_REQUIREMENTS = [r for r in ALL_REQUIREMENTS if r.level == RequirementLevel.MUST]
SHOULD_REQUIREMENTS = [r for r in ALL_REQUIREMENTS if r.level == RequirementLevel.SHOULD]
MAY_REQUIREMENTS = [r for r in ALL_REQUIREMENTS if r.level == RequirementLevel.MAY]

def get_requirements_by_section(section_prefix: str) -> list[RequirementSpec]:
    """Get all requirements for a section (e.g., '3.1')."""
    return [r for r in ALL_REQUIREMENTS if r.section.startswith(section_prefix)]

def get_requirements_by_operation(operation: OperationType) -> list[RequirementSpec]:
    """Get all requirements for an operation type."""
    return [r for r in ALL_REQUIREMENTS if r.operation == operation]
```

### 5.2 Validation Layer

#### 5.2.1 JSON Schema Validator

```python
# tck/validators/json_schema.py
import json
from pathlib import Path
from jsonschema import Draft202012Validator, ValidationError
from dataclasses import dataclass

@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]
    schema_ref: str

class JSONSchemaValidator:
    """Validates JSON responses against a2a.json schema."""

    def __init__(self, schema_path: Path):
        with open(schema_path) as f:
            self.schema = json.load(f)
        self.validator = Draft202012Validator(self.schema)

    def validate(self, response: dict, schema_ref: str) -> ValidationResult:
        """
        Validate a JSON response against a specific schema definition.

        Args:
            response: The JSON response to validate
            schema_ref: JSON pointer to the schema definition (e.g., "#/$defs/Task")

        Returns:
            ValidationResult with valid flag and any errors
        """
        # Resolve the schema reference
        ref_path = schema_ref.lstrip("#/").split("/")
        sub_schema = self.schema
        for part in ref_path:
            sub_schema = sub_schema[part]

        # Validate
        errors = []
        validator = Draft202012Validator(sub_schema, resolver=self.validator.resolver)
        for error in validator.iter_errors(response):
            errors.append(f"{error.json_path}: {error.message}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            schema_ref=schema_ref,
        )
```

#### 5.2.2 Proto Schema Validator

```python
# tck/validators/proto_schema.py
from google.protobuf.message import Message as ProtoMessage
from google.protobuf.descriptor import FieldDescriptor
from dataclasses import dataclass

@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]
    proto_type: str

class ProtoSchemaValidator:
    """Validates gRPC responses against proto message descriptors."""

    def validate(self, response: ProtoMessage, expected_type: type) -> ValidationResult:
        """
        Validate a proto message against expected type and constraints.

        Args:
            response: The proto message to validate
            expected_type: The expected proto message class

        Returns:
            ValidationResult with valid flag and any errors
        """
        errors = []

        # Type check
        if not isinstance(response, expected_type):
            errors.append(
                f"Expected {expected_type.__name__}, got {type(response).__name__}"
            )
            return ValidationResult(False, errors, expected_type.__name__)

        # Validate required fields
        for field in response.DESCRIPTOR.fields:
            if field.label == FieldDescriptor.LABEL_REQUIRED:
                if not response.HasField(field.name):
                    errors.append(f"Missing required field: {field.name}")

        # Validate nested messages recursively
        errors.extend(self._validate_nested(response))

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            proto_type=expected_type.__name__,
        )

    def _validate_nested(self, message: ProtoMessage) -> list[str]:
        """Recursively validate nested messages."""
        errors = []
        for field in message.DESCRIPTOR.fields:
            if field.message_type and message.HasField(field.name):
                nested = getattr(message, field.name)
                errors.extend(self._validate_nested(nested))
        return errors
```

#### 5.2.3 Transport-Specific Validators

```python
# tck/validators/jsonrpc/error_validator.py
from dataclasses import dataclass

# JSON-RPC error code mappings from spec Section 9
JSONRPC_ERROR_CODES = {
    "TaskNotFoundError": -32001,
    "TaskNotCancelableError": -32002,
    "PushNotificationNotSupportedError": -32003,
    "UnsupportedOperationError": -32004,
    "ContentTypeNotSupportedError": -32005,
    "InvalidAgentResponseError": -32006,
    "InvalidRequestError": -32600,
    "MethodNotFoundError": -32601,
    "InvalidParamsError": -32602,
    "InternalError": -32603,
    "VersionNotSupportedError": -32009,
}

@dataclass
class ErrorValidationResult:
    valid: bool
    expected_code: int
    actual_code: int
    message: str

def validate_jsonrpc_error(response: dict, expected_error: str) -> ErrorValidationResult:
    """Validate JSON-RPC error response matches expected error type."""
    if "error" not in response:
        return ErrorValidationResult(
            valid=False,
            expected_code=JSONRPC_ERROR_CODES.get(expected_error, 0),
            actual_code=0,
            message="Response has no error field",
        )

    error = response["error"]
    expected_code = JSONRPC_ERROR_CODES.get(expected_error)
    actual_code = error.get("code")

    return ErrorValidationResult(
        valid=actual_code == expected_code,
        expected_code=expected_code,
        actual_code=actual_code,
        message=error.get("message", ""),
    )
```

```python
# tck/validators/http_json/error_validator.py
from dataclasses import dataclass

# HTTP+JSON status mappings from spec Section 11
HTTP_JSON_ERROR_STATUS = {
    "TaskNotFoundError": 404,
    "TaskNotCancelableError": 400,
    "UnsupportedOperationError": 400,
    "ContentTypeNotSupportedError": 415,
    "VersionNotSupportedError": 400,
    "InvalidRequestError": 400,
    "InternalError": 500,
}

@dataclass
class ProblemDetails:
    """RFC 7807 Problem Details structure."""
    type: str
    title: str
    status: int
    detail: str = ""
    instance: str = ""

@dataclass
class ErrorValidationResult:
    valid: bool
    expected_status: int
    actual_status: int
    problem_details: ProblemDetails | None

def validate_http_json_error(
    response,
    expected_error: str
) -> ErrorValidationResult:
    """Validate HTTP+JSON error response with Problem Details."""
    expected_status = HTTP_JSON_ERROR_STATUS.get(expected_error, 400)
    actual_status = response.status_code

    problem_details = None
    if response.headers.get("Content-Type") == "application/problem+json":
        body = response.json()
        problem_details = ProblemDetails(
            type=body.get("type", ""),
            title=body.get("title", ""),
            status=body.get("status", 0),
            detail=body.get("detail", ""),
            instance=body.get("instance", ""),
        )

    return ErrorValidationResult(
        valid=actual_status == expected_status,
        expected_status=expected_status,
        actual_status=actual_status,
        problem_details=problem_details,
    )
```

### 5.3 Transport Layer

#### 5.3.1 Base Transport Client

```python
# tck/transport/base.py
from abc import ABC, abstractmethod
from typing import Any, Iterator
from dataclasses import dataclass

@dataclass
class TransportResponse:
    """Unified response wrapper preserving native format."""
    transport: str           # "grpc", "jsonrpc", "http+json"
    success: bool
    raw_response: Any        # Native response (proto, dict, Response)
    error: str | None = None

    @property
    def is_streaming(self) -> bool:
        return False

@dataclass
class StreamingResponse(TransportResponse):
    """Response wrapper for streaming operations."""
    events: Iterator[Any] = None

    @property
    def is_streaming(self) -> bool:
        return True

class BaseTransportClient(ABC):
    """Abstract base class for transport clients."""

    def __init__(self, base_url: str):
        self.base_url = base_url

    @abstractmethod
    def send_message(self, request: dict) -> TransportResponse:
        """Execute SendMessage operation."""
        pass

    @abstractmethod
    def send_streaming_message(self, request: dict) -> StreamingResponse:
        """Execute SendStreamingMessage operation."""
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> TransportResponse:
        """Execute GetTask operation."""
        pass

    @abstractmethod
    def list_tasks(self, params: dict) -> TransportResponse:
        """Execute ListTasks operation."""
        pass

    @abstractmethod
    def cancel_task(self, task_id: str) -> TransportResponse:
        """Execute CancelTask operation."""
        pass

    @abstractmethod
    def subscribe_to_task(self, task_id: str) -> StreamingResponse:
        """Execute SubscribeToTask operation."""
        pass

    @abstractmethod
    def get_extended_agent_card(self) -> TransportResponse:
        """Execute GetExtendedAgentCard operation."""
        pass
```

#### 5.3.2 gRPC Client Implementation

```python
# tck/transport/grpc_client.py
import grpc
from tck.transport.base import BaseTransportClient, TransportResponse, StreamingResponse
from specification.generated import a2a_pb2, a2a_pb2_grpc

class GrpcClient(BaseTransportClient):
    """gRPC transport client using generated stubs."""

    def __init__(self, base_url: str):
        super().__init__(base_url)
        # Parse host:port from URL
        host_port = base_url.replace("grpc://", "").replace("http://", "")
        self.channel = grpc.insecure_channel(host_port)
        self.stub = a2a_pb2_grpc.A2AServiceStub(self.channel)
        self.transport = "grpc"

    def send_message(self, request: dict) -> TransportResponse:
        """Execute SendMessage RPC."""
        try:
            proto_request = self._dict_to_proto(request, a2a_pb2.SendMessageRequest)
            response = self.stub.SendMessage(proto_request)
            return TransportResponse(
                transport=self.transport,
                success=True,
                raw_response=response,
            )
        except grpc.RpcError as e:
            return TransportResponse(
                transport=self.transport,
                success=False,
                raw_response=None,
                error=str(e),
            )

    def send_streaming_message(self, request: dict) -> StreamingResponse:
        """Execute SendStreamingMessage RPC with streaming response."""
        try:
            proto_request = self._dict_to_proto(request, a2a_pb2.SendMessageRequest)
            stream = self.stub.SendStreamingMessage(proto_request)
            return StreamingResponse(
                transport=self.transport,
                success=True,
                raw_response=stream,
                events=stream,
            )
        except grpc.RpcError as e:
            return StreamingResponse(
                transport=self.transport,
                success=False,
                raw_response=None,
                error=str(e),
            )

    def _dict_to_proto(self, data: dict, proto_class: type):
        """Convert dict to proto message using json_format."""
        from google.protobuf import json_format
        return json_format.ParseDict(data, proto_class())
```

#### 5.3.3 JSON-RPC Client Implementation

```python
# tck/transport/jsonrpc_client.py
import httpx
from tck.transport.base import BaseTransportClient, TransportResponse, StreamingResponse

class JsonRpcClient(BaseTransportClient):
    """JSON-RPC 2.0 over HTTP transport client."""

    def __init__(self, base_url: str):
        super().__init__(base_url)
        self.client = httpx.Client(base_url=base_url)
        self._request_id = 0
        self.transport = "jsonrpc"

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _call(self, method: str, params: dict) -> dict:
        """Make a JSON-RPC call."""
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params,
        }
        response = self.client.post(
            "/",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        return response.json()

    def send_message(self, request: dict) -> TransportResponse:
        """Execute SendMessage via JSON-RPC."""
        result = self._call("SendMessage", request)

        if "error" in result:
            return TransportResponse(
                transport=self.transport,
                success=False,
                raw_response=result,
                error=result["error"].get("message"),
            )

        return TransportResponse(
            transport=self.transport,
            success=True,
            raw_response=result.get("result"),
        )

    def send_streaming_message(self, request: dict) -> StreamingResponse:
        """Execute SendStreamingMessage with SSE response."""
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "SendStreamingMessage",
            "params": request,
        }

        with self.client.stream(
            "POST",
            "/",
            json=payload,
            headers={"Accept": "text/event-stream"},
        ) as response:
            return StreamingResponse(
                transport="jsonrpc",
                success=True,
                raw_response=response,
                events=self._parse_sse(response),
            )

    def _parse_sse(self, response) -> Iterator[dict]:
        """Parse Server-Sent Events stream."""
        import json
        for line in response.iter_lines():
            if line.startswith("data: "):
                yield json.loads(line[6:])
```

#### 5.3.4 HTTP+JSON Client Implementation

```python
# tck/transport/http_json_client.py
import httpx
from tck.transport.base import BaseTransportClient, TransportResponse, StreamingResponse

class HttpJsonClient(BaseTransportClient):
    """HTTP+JSON transport client."""

    def __init__(self, base_url: str):
        super().__init__(base_url)
        self.client = httpx.Client(base_url=base_url)
        self.transport = "http+json"

    def send_message(self, request: dict) -> TransportResponse:
        """Execute POST /message:send."""
        response = self.client.post(
            "/message:send",
            json=request,
            headers={"Content-Type": "application/json"},
        )

        if response.status_code >= 400:
            return TransportResponse(
                transport=self.transport,
                success=False,
                raw_response=response,
                error=response.text,
            )

        return TransportResponse(
            transport=self.transport,
            success=True,
            raw_response=response.json(),
        )

    def get_task(self, task_id: str) -> TransportResponse:
        """Execute GET /tasks/{id}."""
        response = self.client.get(f"/tasks/{task_id}")

        if response.status_code >= 400:
            return TransportResponse(
                transport=self.transport,
                success=False,
                raw_response=response,
                error=response.text,
            )

        return TransportResponse(
            transport=self.transport",
            success=True,
            raw_response=response.json(),
        )

    def send_streaming_message(self, request: dict) -> StreamingResponse:
        """Execute POST /message:stream with SSE response."""
        with self.client.stream(
            "POST",
            "/message:stream",
            json=request,
            headers={"Accept": "text/event-stream"},
        ) as response:
            return StreamingResponse(
                transport=self.transport",
                success=True,
                raw_response=response,
                events=self._parse_sse(response),
            )
```

### 5.4 Test Layer

#### 5.4.1 Core Parametrized Tests

```python
# tests/core/test_requirements.py
import pytest
from tck.requirements.registry import ALL_REQUIREMENTS, MUST_REQUIREMENTS
from tck.requirements.base import RequirementSpec, RequirementLevel

TRANSPORTS = ["grpc", "jsonrpc", "http+json"]

@pytest.mark.parametrize("transport", TRANSPORTS)
@pytest.mark.parametrize(
    "requirement",
    MUST_REQUIREMENTS,
    ids=lambda r: r.id,
)
def test_must_requirement(
    transport: str,
    requirement: RequirementSpec,
    transport_clients: dict,
    validators: dict,
    compliance_collector,
):
    """Test MUST-level requirements across all transports."""
    # Get transport-specific client and validator
    client = transport_clients[transport]
    validator = validators[transport]

    # Execute the operation
    response = client.execute(requirement.operation, requirement.sample_input)

    # Validate response
    result = validator.validate(response, requirement)

    # Record result for compliance report
    compliance_collector.record(requirement.id, transport, result.valid, result.errors)

    # Assert
    assert result.valid, (
        f"{requirement.id} ({requirement.title}) failed on {transport}:\n"
        f"  Errors: {result.errors}\n"
        f"  Spec: {requirement.spec_url}"
    )


@pytest.mark.parametrize("transport", TRANSPORTS)
@pytest.mark.parametrize(
    "requirement",
    [r for r in ALL_REQUIREMENTS if r.level == RequirementLevel.SHOULD],
    ids=lambda r: r.id,
)
def test_should_requirement(
    transport: str,
    requirement: RequirementSpec,
    transport_clients: dict,
    validators: dict,
    compliance_collector,
):
    """Test SHOULD-level requirements (warnings, not failures)."""
    client = transport_clients[transport]
    validator = validators[transport]

    response = client.execute(requirement.operation, requirement.sample_input)

    result = validator.validate(response, requirement)

    compliance_collector.record(
        requirement.id,
        transport,
        result.valid,
        result.errors,
        level="SHOULD",
    )

    if not result.valid:
        pytest.skip(f"SHOULD requirement not met: {result.errors}")
```

#### 5.4.2 Transport Corner Case Tests

```python
# tests/jsonrpc/test_error_codes.py
import pytest
from tck.validators.jsonrpc.error_validator import (
    validate_jsonrpc_error,
    JSONRPC_ERROR_CODES,
)

class TestJsonRpcErrorCodes:
    """
    Validate JSON-RPC error code mappings per Specification Section 9.

    Reference: https://github.com/a2aproject/A2A/blob/main/docs/specification.md#9-json-rpc-binding
    """

    def test_task_not_found_error(self, jsonrpc_client):
        """TaskNotFoundError MUST return code -32001."""
        response = jsonrpc_client.get_task("nonexistent-task-id")
        result = validate_jsonrpc_error(response.raw_response, "TaskNotFoundError")

        assert result.valid, (
            f"Expected error code {result.expected_code}, "
            f"got {result.actual_code}"
        )

    def test_unsupported_operation_error(self, jsonrpc_client, agent_card):
        """UnsupportedOperationError MUST return code -32004."""
        # Find an unsupported operation based on agent card capabilities
        if agent_card.capabilities.streaming:
            pytest.skip("Agent supports streaming")

        response = jsonrpc_client.send_streaming_message({"message": {}})
        result = validate_jsonrpc_error(response.raw_response, "UnsupportedOperationError")

        assert result.valid

    @pytest.mark.parametrize("error_type,expected_code", [
        ("TaskNotFoundError", -32001),
        ("TaskNotCancelableError", -32002),
        ("UnsupportedOperationError", -32004),
        ("ContentTypeNotSupportedError", -32005),
        ("VersionNotSupportedError", -32009),
    ])
    def test_error_code_mapping(self, error_type, expected_code):
        """Verify error code registry matches spec."""
        assert JSONRPC_ERROR_CODES[error_type] == expected_code
```

```python
# tests/http_json/test_http_status.py
import pytest
from tck.validators.http_json.error_validator import validate_http_json_error, HTTP_JSON_ERROR_STATUS

class TestHttpJsonStatus:
    """
    Validate HTTP+JSON status code mappings per Specification Section 11.

    Reference: https://github.com/a2aproject/A2A/blob/main/docs/specification.md#11-rest-binding
    """

    def test_task_not_found_returns_404(self, rest_client):
        """TaskNotFoundError MUST return HTTP 404."""
        response = rest_client.get_task("nonexistent-task-id")
        result = validate_rest_error(response.raw_response, "TaskNotFoundError")

        assert result.valid, (
            f"Expected HTTP {result.expected_status}, "
            f"got {result.actual_status}"
        )

    def test_problem_details_format(self, rest_client):
        """Error responses SHOULD use RFC 7807 Problem Details."""
        response = rest_client.get_task("nonexistent-task-id")
        result = validate_rest_error(response.raw_response, "TaskNotFoundError")

        assert result.problem_details is not None, "Missing Problem Details"
        assert result.problem_details.type == "TaskNotFoundError"
        assert result.problem_details.status == 404
```

### 5.5 Reporting Layer

#### 5.5.1 Compliance Report Structure

```python
# tck/reporting/collector.py
from dataclasses import dataclass, field
from typing import Literal

@dataclass
class TestResult:
    requirement_id: str
    transport: str
    passed: bool
    errors: list[str]
    level: Literal["MUST", "SHOULD", "MAY"] = "MUST"

@dataclass
class ComplianceReport:
    """Complete compliance report structure."""

    # Summary
    timestamp: str
    sut_url: str
    spec_version: str = "1.0"

    # Per-requirement view
    per_requirement: dict[str, dict[str, str]] = field(default_factory=dict)
    # e.g., {"REQ-3.1": {"grpc": "PASS", "jsonrpc": "PASS", "rest": "FAIL"}}

    # Per-transport view
    per_transport: dict[str, dict[str, int]] = field(default_factory=dict)
    # e.g., {"grpc": {"passed": 100, "failed": 0, "total": 100}}

    # Corner cases
    corner_cases: dict[str, dict[str, str]] = field(default_factory=dict)

    # Aggregates
    overall_compliance: float = 0.0
    must_compliance: float = 0.0
    should_compliance: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "summary": {
                "timestamp": self.timestamp,
                "sut_url": self.sut_url,
                "spec_version": self.spec_version,
                "overall_compliance": f"{self.overall_compliance:.1%}",
                "must_compliance": f"{self.must_compliance:.1%}",
                "should_compliance": f"{self.should_compliance:.1%}",
            },
            "per_requirement": self.per_requirement,
            "per_transport": self.per_transport,
            "corner_cases": self.corner_cases,
        }
```

---

## 6. Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

**Goal**: Establish project structure and specification integration.

| Task | Description | Deliverable |
|------|-------------|-------------|
| 1.1 | Create project structure | Directory layout per Section 4.2 |
| 1.2 | Set up pyproject.toml | Build configuration with dependencies |
| 1.3 | Sync specification artifacts | Local copies of a2a.proto |
| 1.4 | Generate Python proto stubs | a2a_pb2.py, a2a_pb2_grpc.py |
| 1.5 | Generate derived JSON schema | a2a.json |
| 1.6 | Implement RequirementSpec base | Base class per Section 5.1.1 |
| 1.7 | Create requirement registry skeleton | Empty registry with structure |

**Dependencies**: None

**Acceptance Criteria**:
- `pip install -e .` succeeds
- Proto stubs compile without errors
- Basic pytest runs (no tests yet)

---

### Phase 2: Validation Layer (Weeks 3-4)

**Goal**: Implement schema validation for all transports.

| Task | Description | Deliverable |
|------|-------------|-------------|
| 2.1 | Implement JSONSchemaValidator | JSON Schema validation using a2a.json |
| 2.2 | Implement ProtoSchemaValidator | Proto descriptor validation |
| 2.3 | Implement JSON-RPC error validator | Error code validation per Section 9 |
| 2.4 | Implement REST error validator | HTTP status + Problem Details per Section 11 |
| 2.5 | Write validator unit tests | Test validators with mock data |

**Dependencies**: Phase 1

**Acceptance Criteria**:
- Validators correctly identify valid/invalid responses
- Error messages are clear and actionable
- Unit tests pass for all validators

---

### Phase 3: Transport Layer (Weeks 5-6)

**Goal**: Implement native transport clients.

| Task | Description | Deliverable |
|------|-------------|-------------|
| 3.1 | Implement BaseTransportClient | Abstract base class |
| 3.2 | Implement GrpcClient | gRPC client using generated stubs |
| 3.3 | Implement JsonRpcClient | JSON-RPC over HTTP client |
| 3.4 | Implement HttpJsonClient | HTTP+JSON client |
| 3.5 | Implement TransportManager | Client orchestration |
| 3.6 | Write transport integration tests | Test against mock server |

**Dependencies**: Phase 1, Phase 2 (for validation)

**Acceptance Criteria**:
- All clients can connect to a test server
- Operations execute without transport errors
- Streaming operations work correctly

---

### Phase 4: Requirement Definitions (Weeks 7-8)

**Goal**: Define all ~100 requirements from specification.

| Task | Description | Deliverable |
|------|-------------|-------------|
| 4.1 | Define Section 3 requirements | Core operations (SendMessage, GetTask, etc.) |
| 4.2 | Define Section 4 requirements | Object structure (Task, Message, Part, etc.) |
| 4.3 | Define Section 5 requirements | AgentCard and capabilities |
| 4.4 | Define Section 6-8 requirements | Security, streaming, push notifications |
| 4.5 | Define Section 9-11 requirements | Transport-specific bindings |
| 4.6 | Create requirement registry | ALL_REQUIREMENTS with categorization |

**Dependencies**: Phase 1

**Acceptance Criteria**:
- All MUST requirements from spec are defined
- Each requirement has valid sample input
- Requirements link to spec sections

---

### Phase 5: Core Test Implementation (Weeks 9-10)

**Goal**: Implement parametrized requirement tests.

| Task | Description | Deliverable |
|------|-------------|-------------|
| 5.1 | Implement conftest.py fixtures | Transport clients, validators, collectors |
| 5.2 | Implement test_requirements.py | Parametrized tests per Section 5.4.1 |
| 5.3 | Implement compliance collector | Test result collection |
| 5.4 | Add pytest markers | Requirement level markers |
| 5.5 | Implement CLI runner | run_tck.py with options |

**Dependencies**: Phase 2, 3, 4

**Acceptance Criteria**:
- `pytest tests/core/` runs all parametrized tests
- Results are collected per-requirement and per-transport
- CLI provides transport and category filtering

---

### Phase 6: Corner Case Tests (Weeks 11-12)

**Goal**: Implement transport-specific corner case tests.

| Task | Description | Deliverable |
|------|-------------|-------------|
| 6.1 | Implement JSON-RPC error code tests | tests/jsonrpc/test_error_codes.py |
| 6.2 | Implement JSON-RPC SSE streaming tests | tests/jsonrpc/test_sse_streaming.py |
| 6.3 | Implement HTTP+JSON status tests | tests/http_json/test_http_status.py |
| 6.4 | Implement HTTP+JSON Problem Details tests | tests/http_json/test_problem_details.py |
| 6.5 | Implement gRPC status code tests | tests/grpc/test_status_codes.py |
| 6.6 | Implement gRPC streaming tests | tests/grpc/test_streaming.py |

**Dependencies**: Phase 3, 5

**Acceptance Criteria**:
- All transport-specific error mappings are tested
- Streaming behaviors are validated per transport
- Corner cases document transport differences

---

### Phase 7: Reporting Layer (Weeks 13-14)

**Goal**: Implement compliance reporting.

| Task | Description | Deliverable |
|------|-------------|-------------|
| 7.1 | Implement ComplianceAggregator | Result aggregation logic |
| 7.2 | Implement JSON formatter | compliance.json output |
| 7.3 | Implement HTML formatter | compliance.html output |
| 7.4 | Implement console summary | Terminal output |
| 7.5 | Integrate with pytest hooks | Automatic report generation |
| 7.6 | Generate junitreport.xml | report.html output |

**Dependencies**: Phase 5, 6

**Acceptance Criteria**:
- Reports show per-requirement and per-transport views
- JSON report is machine-parseable
- HTML report is human-readable
- junitreport.xml can be passed to tools to get HTML report

---

### Phase 8: Polish and Documentation (Weeks 15-16)

**Goal**: Finalize for release.

| Task | Description | Deliverable |
|------|-------------|-------------|
| 8.1 | Write README.md | Usage instructions |
| 8.2 | Write CONTRIBUTING.md | Development guide |
| 8.3 | Add CI configuration | GitHub Actions workflow |
| 8.4 | Performance optimization | Test execution speed |
| 8.5 | Error message improvements | Clear, actionable errors |
| 8.6 | Final testing with real SUT | End-to-end validation |

**Dependencies**: All previous phases

**Acceptance Criteria**:
- Documentation is complete and accurate
- CI runs successfully
- TCK validates a reference implementation

---

## 7. Testing Strategy

### 7.1 Test Categories

| Category | Purpose | Location |
|----------|---------|----------|
| **Unit Tests** | Validator logic, requirement parsing | `tests/unit/` |
| **Integration Tests** | Transport clients, end-to-end flows | `tests/integration/` |
| **Core Requirement Tests** | Spec compliance (parametrized) | `tests/core/` |
| **Corner Case Tests** | Transport-specific behaviors | `tests/{transport}/` |

### 7.2 Test Fixtures

```python
# tests/conftest.py
import pytest
from tck.transport.grpc_client import GrpcClient
from tck.transport.jsonrpc_client import JsonRpcClient
from tck.transport.rest_client import RestClient
from tck.validators.json_schema import JSONSchemaValidator
from tck.validators.proto_schema import ProtoSchemaValidator

def pytest_addoption(parser):
    parser.addoption("--sut-url", required=True, help="SUT base URL")
    parser.addoption("--transport", default="all", help="Transport to test")
    parser.addoption("--compliance-report", help="Output report path")

@pytest.fixture(scope="session")
def sut_url(request):
    return request.config.getoption("--sut-url")

@pytest.fixture(scope="session")
def transport_clients(sut_url):
    return {
        "grpc": GrpcClient(sut_url),
        "jsonrpc": JsonRpcClient(sut_url),
        "rest": RestClient(sut_url),
    }

@pytest.fixture(scope="session")
def validators():
    return {
        "grpc": ProtoSchemaValidator(),
        "jsonrpc": JSONSchemaValidator("specification/a2a.json"),
        "rest": JSONSchemaValidator("specification/a2a.json"),
    }

@pytest.fixture(scope="session")
def compliance_collector():
    from tck.reporting.collector import ComplianceCollector
    return ComplianceCollector()
```

### 7.3 Running Tests

```bash
# Run all tests against a SUT
pytest tests/ --sut-url http://localhost:9999

# Run only gRPC tests
pytest tests/ --sut-url http://localhost:9999 --transport grpc

# Run with compliance report
pytest tests/ --sut-url http://localhost:9999 --compliance-report report.json

# Run only MUST requirements
pytest tests/core/ --sut-url http://localhost:9999 -m must

# Run specific requirement
pytest tests/core/ --sut-url http://localhost:9999 -k "REQ-3.1"
```

---

## 8. Appendices

### 8.1 Specification Section Mapping

| Spec Section | Topic | Requirements |
|--------------|-------|--------------|
| 3 | Core Operations | SendMessage, GetTask, ListTasks, CancelTask, SubscribeToTask |
| 4 | Objects | Task, Message, Part, Artifact, AgentCard |
| 5 | Agent Card | Capabilities, Skills, Security Schemes |
| 6 | Security | Authentication, Authorization, TLS |
| 7 | Streaming | SSE, gRPC streams, event ordering |
| 8 | Push Notifications | Webhook configuration, delivery |
| 9 | JSON-RPC Binding | Method names, error codes, headers |
| 10 | gRPC Binding | Service definition, status codes |
| 11 | REST Binding | Endpoints, HTTP methods, Problem Details |

### 8.2 Error Code Reference

**JSON-RPC (Section 9)**:
| Error | Code |
|-------|------|
| TaskNotFoundError | -32001 |
| TaskNotCancelableError | -32002 |
| PushNotificationNotSupportedError | -32003 |
| UnsupportedOperationError | -32004 |
| ContentTypeNotSupportedError | -32005 |
| InvalidAgentResponseError | -32006 |
| VersionNotSupportedError | -32009 |

**REST (Section 11)**:
| Error | HTTP Status |
|-------|-------------|
| TaskNotFoundError | 404 |
| TaskNotCancelableError | 400 |
| UnsupportedOperationError | 400 |
| ContentTypeNotSupportedError | 415 |
| VersionNotSupportedError | 400 |

### 8.3 Architecture Diagrams

- [Overall Architecture](./architecture.mmd)
- [Validation Flow](./validation-flow.mmd)
- [Test Parametrization](./test-parametrization.mmd)
- [Compliance Reporting](./compliance-report.mmd)

### 8.4 Glossary

| Term | Definition |
|------|------------|
| **TCK** | Technology Compatibility Kit - test suite for spec compliance |
| **SUT** | System Under Test - the A2A server being validated |
| **Proto** | Protocol Buffers - the canonical message format |
| **Binding** | Transport-specific protocol mapping |
| **Corner Case** | Transport-specific behavior not covered by core tests |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0-draft | 2025-01-27 | Initial draft from brainstorming session |
