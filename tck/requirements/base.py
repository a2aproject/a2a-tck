"""Base classes for specification requirements.

This module defines the core dataclasses for specifying A2A protocol requirements,
following PRD Section 5.1.1.
"""

from __future__ import annotations

import uuid

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Callable


# Session-unique suffix appended to all sample_input IDs so that
# separate TCK runs never collide with stale tasks on the SUT.
_SESSION = uuid.uuid4().hex[:8]


def tck_id(name: str) -> str:
    """Generate a session-unique TCK identifier.

    Each test run produces fresh IDs, preventing collisions with tasks
    left over from previous runs on the same SUT.
    """
    return f"tck-{name}-{_SESSION}"


class RequirementLevel(Enum):
    """RFC 2119 requirement levels."""

    MUST = "MUST"
    SHOULD = "SHOULD"
    MAY = "MAY"


class OperationType(Enum):
    """A2A protocol operation types."""

    SEND_MESSAGE = "SendMessage"
    SEND_STREAMING_MESSAGE = "SendStreamingMessage"
    GET_TASK = "GetTask"
    LIST_TASKS = "ListTasks"
    CANCEL_TASK = "CancelTask"
    SUBSCRIBE_TO_TASK = "SubscribeToTask"
    CREATE_PUSH_CONFIG = "CreateTaskPushNotificationConfig"
    GET_PUSH_CONFIG = "GetTaskPushNotificationConfig"
    LIST_PUSH_CONFIGS = "ListTaskPushNotificationConfigs"
    DELETE_PUSH_CONFIG = "DeleteTaskPushNotificationConfig"
    GET_EXTENDED_AGENT_CARD = "GetExtendedAgentCard"


# HTTP method constants.
HTTP_GET = "GET"
HTTP_POST = "POST"
HTTP_DELETE = "DELETE"

# REST URL path constants.
PATH_MESSAGE_SEND = "/message:send"
PATH_MESSAGE_STREAM = "/message:stream"
PATH_TASKS = "/tasks"
PATH_TASK = "/tasks/{id}"
PATH_TASK_CANCEL = "/tasks/{id}:cancel"
PATH_TASK_SUBSCRIBE = "/tasks/{id}:subscribe"
PATH_PUSH_CONFIGS = "/tasks/{id}/pushNotificationConfigs"
PATH_PUSH_CONFIG = "/tasks/{id}/pushNotificationConfigs/{configId}"
PATH_EXTENDED_AGENT_CARD = "/extendedAgentCard"


@dataclass
class TransportBinding:
    """Transport-specific binding information for an operation."""

    grpc_rpc: str
    jsonrpc_method: str
    http_json_method: str
    http_json_path: str


@dataclass
class RequirementSpec:
    """Specification for a testable A2A protocol requirement."""

    id: str
    section: str
    title: str
    level: RequirementLevel
    description: str
    operation: OperationType | None = None
    binding: TransportBinding | None = None
    proto_request_type: str = ""
    proto_response_type: str = ""
    json_schema_ref: str = ""
    sample_input: dict = field(default_factory=dict)
    expected_behavior: str = ""
    expected_error: ErrorBinding | None = None
    spec_url: str = ""
    tags: list[str] = field(default_factory=list)
    validators: list[Callable[[Any, str], list[str]]] = field(default_factory=list)


# Shared spec URL base pointing to the local specification file.
SPEC_BASE = "specification/specification.md#"


# Pre-defined TransportBinding constants for the 11 A2A operations.
SEND_MESSAGE_BINDING = TransportBinding(
    grpc_rpc=OperationType.SEND_MESSAGE.value,
    jsonrpc_method=OperationType.SEND_MESSAGE.value,
    http_json_method=HTTP_POST,
    http_json_path=PATH_MESSAGE_SEND,
)

SEND_STREAMING_MESSAGE_BINDING = TransportBinding(
    grpc_rpc=OperationType.SEND_STREAMING_MESSAGE.value,
    jsonrpc_method=OperationType.SEND_STREAMING_MESSAGE.value,
    http_json_method=HTTP_POST,
    http_json_path=PATH_MESSAGE_STREAM,
)

GET_TASK_BINDING = TransportBinding(
    grpc_rpc=OperationType.GET_TASK.value,
    jsonrpc_method=OperationType.GET_TASK.value,
    http_json_method=HTTP_GET,
    http_json_path=PATH_TASK,
)

LIST_TASKS_BINDING = TransportBinding(
    grpc_rpc=OperationType.LIST_TASKS.value,
    jsonrpc_method=OperationType.LIST_TASKS.value,
    http_json_method=HTTP_GET,
    http_json_path=PATH_TASKS,
)

CANCEL_TASK_BINDING = TransportBinding(
    grpc_rpc=OperationType.CANCEL_TASK.value,
    jsonrpc_method=OperationType.CANCEL_TASK.value,
    http_json_method=HTTP_POST,
    http_json_path=PATH_TASK_CANCEL,
)

SUBSCRIBE_TO_TASK_BINDING = TransportBinding(
    grpc_rpc=OperationType.SUBSCRIBE_TO_TASK.value,
    jsonrpc_method=OperationType.SUBSCRIBE_TO_TASK.value,
    http_json_method=HTTP_POST,
    http_json_path=PATH_TASK_SUBSCRIBE,
)

CREATE_PUSH_CONFIG_BINDING = TransportBinding(
    grpc_rpc=OperationType.CREATE_PUSH_CONFIG.value,
    jsonrpc_method=OperationType.CREATE_PUSH_CONFIG.value,
    http_json_method=HTTP_POST,
    http_json_path=PATH_PUSH_CONFIGS,
)

GET_PUSH_CONFIG_BINDING = TransportBinding(
    grpc_rpc=OperationType.GET_PUSH_CONFIG.value,
    jsonrpc_method=OperationType.GET_PUSH_CONFIG.value,
    http_json_method=HTTP_GET,
    http_json_path=PATH_PUSH_CONFIG,
)

LIST_PUSH_CONFIGS_BINDING = TransportBinding(
    grpc_rpc=OperationType.LIST_PUSH_CONFIGS.value,
    jsonrpc_method=OperationType.LIST_PUSH_CONFIGS.value,
    http_json_method=HTTP_GET,
    http_json_path=PATH_PUSH_CONFIGS,
)

DELETE_PUSH_CONFIG_BINDING = TransportBinding(
    grpc_rpc=OperationType.DELETE_PUSH_CONFIG.value,
    jsonrpc_method=OperationType.DELETE_PUSH_CONFIG.value,
    http_json_method=HTTP_DELETE,
    http_json_path=PATH_PUSH_CONFIG,
)

GET_EXTENDED_AGENT_CARD_BINDING = TransportBinding(
    grpc_rpc=OperationType.GET_EXTENDED_AGENT_CARD.value,
    jsonrpc_method=OperationType.GET_EXTENDED_AGENT_CARD.value,
    http_json_method=HTTP_GET,
    http_json_path=PATH_EXTENDED_AGENT_CARD,
)


# ---------------------------------------------------------------------------
# Task state bindings
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskStateBinding:
    """Transport-specific binding for a task state.

    ``json_value`` is the ProtoJSON enum name (SCREAMING_SNAKE_CASE) used
    in JSON-RPC and HTTP+JSON responses per spec Section 5.5.
    ``grpc_value`` is the integer enum value from the ``TaskState``
    protobuf enum.
    """

    json_value: str
    grpc_value: int


TASK_STATE_SUBMITTED = TaskStateBinding(json_value="TASK_STATE_SUBMITTED", grpc_value=1)
TASK_STATE_WORKING = TaskStateBinding(json_value="TASK_STATE_WORKING", grpc_value=2)
TASK_STATE_COMPLETED = TaskStateBinding(json_value="TASK_STATE_COMPLETED", grpc_value=3)
TASK_STATE_FAILED = TaskStateBinding(json_value="TASK_STATE_FAILED", grpc_value=4)
TASK_STATE_CANCELED = TaskStateBinding(json_value="TASK_STATE_CANCELED", grpc_value=5)
TASK_STATE_INPUT_REQUIRED = TaskStateBinding(json_value="TASK_STATE_INPUT_REQUIRED", grpc_value=6)
TASK_STATE_REJECTED = TaskStateBinding(json_value="TASK_STATE_REJECTED", grpc_value=7)
TASK_STATE_AUTH_REQUIRED = TaskStateBinding(json_value="TASK_STATE_AUTH_REQUIRED", grpc_value=8)

TERMINAL_STATES = frozenset({
    TASK_STATE_COMPLETED,
    TASK_STATE_FAILED,
    TASK_STATE_CANCELED,
    TASK_STATE_REJECTED,
})


# ---------------------------------------------------------------------------
# Error bindings (spec Section 5.4)
# ---------------------------------------------------------------------------

A2A_ERROR_DOMAIN = "a2a-protocol.org"


@dataclass
class ErrorBinding:
    """Transport-specific error code binding for an A2A error type (spec Section 5.4).

    The ``reason`` field is the ErrorInfo reason string used in
    ``google.rpc.ErrorInfo`` across all transports (UPPER_SNAKE_CASE
    without the "Error" suffix).  It is only set for A2A-specific errors;
    standard JSON-RPC errors leave it as ``None``.
    """

    name: str
    jsonrpc_code: int
    http_status: int
    grpc_status: str
    reason: str | None = None

    def expected_code(self, transport: str) -> int | str | None:
        """Return the expected error code for the given transport."""
        if transport == "jsonrpc":
            return self.jsonrpc_code
        if transport == "http_json":
            return self.http_status
        if transport == "grpc":
            return self.grpc_status
        return None


# A2A-specific errors
TASK_NOT_FOUND_ERROR = ErrorBinding(
    name="TaskNotFoundError",
    jsonrpc_code=-32001,
    http_status=404,
    grpc_status="NOT_FOUND",
    reason="TASK_NOT_FOUND",
)

TASK_NOT_CANCELABLE_ERROR = ErrorBinding(
    name="TaskNotCancelableError",
    jsonrpc_code=-32002,
    http_status=409,
    grpc_status="FAILED_PRECONDITION",
    reason="TASK_NOT_CANCELABLE",
)

PUSH_NOTIFICATION_NOT_SUPPORTED_ERROR = ErrorBinding(
    name="PushNotificationNotSupportedError",
    jsonrpc_code=-32003,
    http_status=400,
    grpc_status="UNIMPLEMENTED",
    reason="PUSH_NOTIFICATION_NOT_SUPPORTED",
)

UNSUPPORTED_OPERATION_ERROR = ErrorBinding(
    name="UnsupportedOperationError",
    jsonrpc_code=-32004,
    http_status=400,
    grpc_status="UNIMPLEMENTED",
    reason="UNSUPPORTED_OPERATION",
)

CONTENT_TYPE_NOT_SUPPORTED_ERROR = ErrorBinding(
    name="ContentTypeNotSupportedError",
    jsonrpc_code=-32005,
    http_status=415,
    grpc_status="INVALID_ARGUMENT",
    reason="CONTENT_TYPE_NOT_SUPPORTED",
)

INVALID_AGENT_RESPONSE_ERROR = ErrorBinding(
    name="InvalidAgentResponseError",
    jsonrpc_code=-32006,
    http_status=502,
    grpc_status="INTERNAL",
    reason="INVALID_AGENT_RESPONSE",
)

EXTENDED_AGENT_CARD_NOT_CONFIGURED_ERROR = ErrorBinding(
    name="ExtendedAgentCardNotConfiguredError",
    jsonrpc_code=-32007,
    http_status=400,
    grpc_status="FAILED_PRECONDITION",
    reason="EXTENDED_AGENT_CARD_NOT_CONFIGURED",
)

EXTENSION_SUPPORT_REQUIRED_ERROR = ErrorBinding(
    name="ExtensionSupportRequiredError",
    jsonrpc_code=-32008,
    http_status=400,
    grpc_status="FAILED_PRECONDITION",
    reason="EXTENSION_SUPPORT_REQUIRED",
)

VERSION_NOT_SUPPORTED_ERROR = ErrorBinding(
    name="VersionNotSupportedError",
    jsonrpc_code=-32009,
    http_status=400,
    grpc_status="UNIMPLEMENTED",
    reason="VERSION_NOT_SUPPORTED",
)

# Standard JSON-RPC errors (no ErrorInfo reason or gRPC mapping)
INVALID_REQUEST_ERROR = ErrorBinding(
    name="InvalidRequestError",
    jsonrpc_code=-32600,
    http_status=400,
    grpc_status="",
)

METHOD_NOT_FOUND_ERROR = ErrorBinding(
    name="MethodNotFoundError",
    jsonrpc_code=-32601,
    http_status=404,
    grpc_status="",
)

INVALID_PARAMS_ERROR = ErrorBinding(
    name="InvalidParamsError",
    jsonrpc_code=-32602,
    http_status=400,
    grpc_status="",
)

INTERNAL_ERROR = ErrorBinding(
    name="InternalError",
    jsonrpc_code=-32603,
    http_status=500,
    grpc_status="",
)

PARSE_ERROR = ErrorBinding(
    name="ParseError",
    jsonrpc_code=-32700,
    http_status=0,
    grpc_status="",
)

# Collection of all error bindings keyed by error name.
ERROR_BINDINGS: dict[str, ErrorBinding] = {
    e.name: e
    for e in [
        TASK_NOT_FOUND_ERROR,
        TASK_NOT_CANCELABLE_ERROR,
        PUSH_NOTIFICATION_NOT_SUPPORTED_ERROR,
        UNSUPPORTED_OPERATION_ERROR,
        CONTENT_TYPE_NOT_SUPPORTED_ERROR,
        INVALID_AGENT_RESPONSE_ERROR,
        EXTENDED_AGENT_CARD_NOT_CONFIGURED_ERROR,
        EXTENSION_SUPPORT_REQUIRED_ERROR,
        VERSION_NOT_SUPPORTED_ERROR,
        INVALID_REQUEST_ERROR,
        METHOD_NOT_FOUND_ERROR,
        INVALID_PARAMS_ERROR,
        INTERNAL_ERROR,
        PARSE_ERROR,
    ]
}

# Set of A2A error reasons (excludes standard JSON-RPC errors which have no reason).
A2A_ERROR_REASONS: set[str] = {e.reason for e in ERROR_BINDINGS.values() if e.reason is not None}
