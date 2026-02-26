"""JSON-RPC protocol binding requirements from A2A specification Section 9.

Covers: JSON-RPC 2.0 format, Content-Type, PascalCase methods,
error codes, SSE streaming format.
"""

from tck.requirements.base import (
    SPEC_BASE,
    RequirementLevel,
    RequirementSpec,
)
from tck.requirements.tags import (
    CODE,
    CONTENT_TYPE,
    ERROR,
    FORMAT,
    JSONRPC,
    MAPPING,
    METHOD,
    SERVICE_PARAMS,
    SSE,
    STREAMING,
)


BINDING_JSONRPC_REQUIREMENTS: list[RequirementSpec] = [
    RequirementSpec(
        id="JSONRPC-FMT-001",
        section="9.1",
        title="Requests use JSON-RPC 2.0 format",
        level=RequirementLevel.MUST,
        description=(
            "All JSON-RPC requests MUST follow the standard JSON-RPC 2.0 "
            "format with jsonrpc, id, method, and params fields."
        ),
        expected_behavior="Requests conform to JSON-RPC 2.0 structure",
        spec_url=f"{SPEC_BASE}93-base-request-structure",
        tags=[JSONRPC, FORMAT],
    ),
    RequirementSpec(
        id="JSONRPC-FMT-002",
        section="9.1",
        title="Content-Type is application/json",
        level=RequirementLevel.MUST,
        description=(
            "JSON-RPC requests and responses MUST use Content-Type "
            "application/json."
        ),
        expected_behavior="Content-Type header is application/json",
        spec_url=f"{SPEC_BASE}91-protocol-requirements",
        tags=[JSONRPC, FORMAT, CONTENT_TYPE],
    ),
    RequirementSpec(
        id="JSONRPC-SVC-001",
        section="9.1",
        title="Method names use PascalCase matching gRPC conventions",
        level=RequirementLevel.MUST,
        description=(
            "JSON-RPC method names MUST use PascalCase matching gRPC "
            "conventions (e.g., SendMessage, GetTask)."
        ),
        expected_behavior="Methods named in PascalCase",
        spec_url=f"{SPEC_BASE}91-protocol-requirements",
        tags=[JSONRPC, METHOD],
    ),
    RequirementSpec(
        id="JSONRPC-SVC-002",
        section="9.2",
        title="Service parameters transmitted as HTTP headers",
        level=RequirementLevel.MUST,
        description=(
            "A2A service parameters MUST be transmitted using standard HTTP "
            "request headers for JSON-RPC binding."
        ),
        expected_behavior="A2A-Version and A2A-Extensions sent as HTTP headers",
        spec_url=f"{SPEC_BASE}92-service-parameter-transmission",
        tags=[JSONRPC, SERVICE_PARAMS],
    ),
    RequirementSpec(
        id="JSONRPC-ERR-001",
        section="9.5",
        title="Error responses use JSON-RPC 2.0 error object structure",
        level=RequirementLevel.MUST,
        description=(
            "JSON-RPC error responses MUST use the standard JSON-RPC 2.0 "
            "error object structure with code, message, and optional data."
        ),
        expected_behavior="Errors include numeric code, message, optional data",
        spec_url=f"{SPEC_BASE}95-error-handling",
        tags=[JSONRPC, ERROR],
    ),
    RequirementSpec(
        id="JSONRPC-ERR-002",
        section="9.5",
        title="A2A-specific errors use codes -32001 to -32099",
        level=RequirementLevel.MUST,
        description=(
            "A2A-specific errors MUST use error codes in the range -32001 to "
            "-32099 as defined in the error code mappings."
        ),
        expected_behavior="A2A error codes within specified range",
        spec_url=f"{SPEC_BASE}95-error-handling",
        tags=[JSONRPC, ERROR, CODE],
    ),
    RequirementSpec(
        id="JSONRPC-SSE-001",
        section="9.4.2",
        title="Streaming uses Server-Sent Events with text/event-stream",
        level=RequirementLevel.MUST,
        description=(
            "JSON-RPC streaming responses MUST use Server-Sent Events with "
            "Content-Type text/event-stream. Each SSE data line contains "
            "a JSON-RPC response wrapping a StreamResponse object."
        ),
        expected_behavior="SSE stream with JSON-RPC wrapped StreamResponse events",
        spec_url=f"{SPEC_BASE}942-sendstreamingmessage",
        tags=[JSONRPC, STREAMING, SSE],
    ),
    RequirementSpec(
        id="JSONRPC-SSE-002",
        section="5.4",
        title="A2A error types mapped to correct JSON-RPC error codes",
        level=RequirementLevel.MUST,
        description=(
            "All A2A-specific error types MUST be mapped to their specified "
            "JSON-RPC error codes: TaskNotFoundError=-32001, "
            "TaskNotCancelableError=-32002, "
            "PushNotificationNotSupportedError=-32003, "
            "UnsupportedOperationError=-32004, "
            "ContentTypeNotSupportedError=-32005, "
            "InvalidAgentResponseError=-32006, "
            "ExtendedAgentCardNotConfiguredError=-32007, "
            "ExtensionSupportRequiredError=-32008, "
            "VersionNotSupportedError=-32009."
        ),
        expected_behavior="Each A2A error mapped to correct numeric code",
        spec_url=f"{SPEC_BASE}54-error-code-mappings",
        tags=[JSONRPC, ERROR, MAPPING],
    ),
]
