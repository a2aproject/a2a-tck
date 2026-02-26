"""Base classes for specification requirements.

This module defines the core dataclasses for specifying A2A protocol requirements,
following PRD Section 5.1.1.
"""

from dataclasses import dataclass, field
from enum import Enum


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
    LIST_PUSH_CONFIGS = "ListTaskPushNotificationConfig"
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
    spec_url: str = ""
    tags: list[str] = field(default_factory=list)


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
