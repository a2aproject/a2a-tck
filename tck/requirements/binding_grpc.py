"""gRPC protocol binding requirements from A2A specification Section 10.

Covers: A2AService conformance, Protobuf v3, gRPC metadata for
service params, ErrorInfo details.
"""

from tck.requirements.base import (
    SPEC_BASE,
    RequirementLevel,
    RequirementSpec,
)
from tck.requirements.tags import (
    ERROR,
    ERRORINFO,
    GRPC,
    MAPPING,
    METADATA,
    PROTOBUF,
    SERVICE,
    SERVICE_PARAMS,
    STREAMING,
    TLS,
    TRANSPORT,
)


BINDING_GRPC_REQUIREMENTS: list[RequirementSpec] = [
    RequirementSpec(
        id="GRPC-SVC-001",
        section="10.1",
        title="Implement A2AService gRPC service",
        level=RequirementLevel.MUST,
        description=(
            "gRPC binding implementations MUST implement the A2AService "
            "gRPC service as defined in the normative a2a.proto file."
        ),
        expected_behavior="A2AService gRPC service fully implemented",
        spec_url=f"{SPEC_BASE}101-protocol-requirements",
        tags=[GRPC, SERVICE],
    ),
    RequirementSpec(
        id="GRPC-SVC-002",
        section="10.1",
        title="Use Protocol Buffers version 3 serialization",
        level=RequirementLevel.MUST,
        description=(
            "gRPC binding MUST use Protocol Buffers version 3 for "
            "serialization."
        ),
        expected_behavior="Proto3 serialization used",
        spec_url=f"{SPEC_BASE}101-protocol-requirements",
        tags=[GRPC, PROTOBUF],
    ),
    RequirementSpec(
        id="GRPC-SVC-003",
        section="10.1",
        title="gRPC over HTTP/2 with TLS",
        level=RequirementLevel.MUST,
        description=(
            "gRPC binding MUST use gRPC over HTTP/2 with TLS."
        ),
        expected_behavior="Communication over HTTP/2 with TLS",
        spec_url=f"{SPEC_BASE}101-protocol-requirements",
        tags=[GRPC, TRANSPORT, TLS],
    ),
    RequirementSpec(
        id="GRPC-META-001",
        section="10.2",
        title="Service parameters transmitted as gRPC metadata",
        level=RequirementLevel.MUST,
        description=(
            "A2A service parameters MUST be transmitted using gRPC metadata "
            "(headers). Service parameter names MUST be transmitted as "
            "gRPC metadata keys."
        ),
        expected_behavior="A2A-Version and A2A-Extensions sent as gRPC metadata",
        spec_url=f"{SPEC_BASE}102-service-parameter-transmission",
        tags=[GRPC, METADATA, SERVICE_PARAMS],
    ),
    RequirementSpec(
        id="GRPC-ERR-001",
        section="10.6",
        title="A2A errors include ErrorInfo in status details",
        level=RequirementLevel.MUST,
        description=(
            "For A2A-specific errors, implementations MUST include a "
            "google.rpc.ErrorInfo message in the status.details array with "
            "reason (UPPER_SNAKE_CASE without Error suffix) and domain "
            "set to 'a2a-protocol.org'."
        ),
        expected_behavior="ErrorInfo with reason and domain in status details",
        spec_url=f"{SPEC_BASE}106-error-handling",
        tags=[GRPC, ERROR, ERRORINFO],
    ),
    RequirementSpec(
        id="GRPC-ERR-002",
        section="5.4",
        title="A2A error types mapped to correct gRPC status codes",
        level=RequirementLevel.MUST,
        description=(
            "All A2A-specific error types MUST be mapped to their specified "
            "gRPC status codes: TaskNotFoundError=NOT_FOUND, "
            "TaskNotCancelableError=FAILED_PRECONDITION, "
            "PushNotificationNotSupportedError=UNIMPLEMENTED, "
            "UnsupportedOperationError=UNIMPLEMENTED, "
            "ContentTypeNotSupportedError=INVALID_ARGUMENT, "
            "InvalidAgentResponseError=INTERNAL, "
            "ExtendedAgentCardNotConfiguredError=FAILED_PRECONDITION, "
            "ExtensionSupportRequiredError=FAILED_PRECONDITION, "
            "VersionNotSupportedError=UNIMPLEMENTED."
        ),
        expected_behavior="Each A2A error mapped to correct gRPC status",
        spec_url=f"{SPEC_BASE}54-error-code-mappings",
        tags=[GRPC, ERROR, MAPPING],
    ),
    RequirementSpec(
        id="GRPC-ERR-003",
        section="10.7",
        title="gRPC streaming uses server streaming RPCs",
        level=RequirementLevel.MUST,
        description=(
            "gRPC streaming MUST use server streaming RPCs for real-time "
            "updates with StreamResponse messages."
        ),
        expected_behavior="Server streaming RPC delivers StreamResponse messages",
        spec_url=f"{SPEC_BASE}107-streaming",
        tags=[GRPC, STREAMING],
    ),
]
