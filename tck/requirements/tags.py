"""Centralized tag constants for requirement specifications.

All tags used by RequirementSpec objects are defined here to avoid
hard-coded strings and enable consistent filtering.
"""

from __future__ import annotations


# --- Domain tags ---
AGENT_CARD = "agent-card"
ARTIFACT = "artifact"
AUTH = "auth"
AUTHORIZATION = "authorization"
CORE = "core"
DATA_MODEL = "data-model"
INTEROP = "interop"
STREAMING = "streaming"
VERSIONING = "versioning"

# --- Operation tags ---
EXECUTION_MODE = "execution-mode"
CANCEL_TASK = "cancel-task"
CREATE = "create"
DELETE = "delete"
DELIVERY = "delivery"
DISCOVERY = "discovery"
GET = "get"
GET_TASK = "get-task"
LIST = "list"
LIST_TASKS = "list-tasks"
SEND_MESSAGE = "send-message"
SUBSCRIBE = "subscribe"

# --- Feature tags ---
CAPABILITY = "capability"
COMPATIBILITY = "compatibility"
CONTEXT = "context"
ENUM = "enum"
HISTORY = "history"
ERROR = "error"
EXTENDED = "extended"
EXTENSION = "extension"
FORMAT = "format"
IDEMPOTENT = "idempotent"
IN_TASK = "in-task"
MESSAGE = "message"
MULTI_STREAM = "multi-stream"
MULTI_TURN = "multi-turn"
ORDERING = "ordering"
PAGINATION = "pagination"
PART = "part"
PUSH_NOTIFICATION = "push-notification"
SCOPE = "scope"
SECURITY = "security"
SERIALIZATION = "serialization"
SIGNING = "signing"
STATUS = "status"
STRUCTURE = "structure"
TASK = "task"
TASK_ID = "task-id"
TIMESTAMP = "timestamp"
VALIDATION = "validation"

# --- Binding tags ---
GRPC = "grpc"
JSONRPC = "jsonrpc"
REST = "rest"

# --- Test strategy tags ---
NOT_AUTOMATABLE = "not-automatable"
MULTI_OPERATION = "multi-operation"

# --- Binding detail tags ---
AIP193 = "aip-193"
CACHING = "caching"
CLIENT = "client"
CODE = "code"
CONTENT_TYPE = "content-type"
DECLARATION = "declaration"
DEFAULT = "default"
EQUIVALENCE = "equivalence"
ERRORINFO = "errorinfo"
INTERFACE = "interface"
JCS = "jcs"
JWS = "jws"
MAPPING = "mapping"
METADATA = "metadata"
METHOD = "method"
PROTOBUF = "protobuf"
PROTOCOL = "protocol"
QUERY_PARAMS = "query-params"
SERVER = "server"
SERVICE = "service"
SERVICE_PARAMS = "service-params"
SSE = "sse"
TLS = "tls"
TRANSPORT = "transport"
URL = "url"
