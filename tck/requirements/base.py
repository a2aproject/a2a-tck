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
    operation: OperationType
    binding: TransportBinding
    proto_request_type: str
    proto_response_type: str
    json_schema_ref: str
    sample_input: dict = field(default_factory=dict)
    expected_behavior: str = ""
    spec_url: str = ""
    tags: list[str] = field(default_factory=list)
