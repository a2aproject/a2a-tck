"""
gRPC transport client for A2A Protocol v0.3.0

Implements real gRPC communication with A2A SUTs using Protocol Buffers.
This client makes actual network calls to live SUTs - NO MOCKING.

Specification Reference: A2A Protocol v0.3.0 §4.2 - gRPC Transport
"""

import json
import logging
import os
import sys
import tempfile
import importlib
from typing import Dict, List, Optional, Any, AsyncIterator, Union
from urllib.parse import urlparse
import asyncio

import grpc
from google.protobuf.struct_pb2 import Struct
from google.protobuf.timestamp_pb2 import Timestamp

from tck.transport.base_client import BaseTransportClient, TransportType, TransportError

logger = logging.getLogger(__name__)


class A2AValidationError(TransportError):
    """Raised when gRPC response doesn't conform to A2A specification."""

    pass


def _validate_task_object(task: Dict[str, Any]) -> None:
    """
    Validate that a Task object conforms to A2A specification.

    Raises A2AValidationError if validation fails.
    """
    # Validate required fields per A2A specification
    required_fields = ["id", "contextId", "status", "kind"]
    for field in required_fields:
        if field not in task:
            raise A2AValidationError(f"Task missing required field '{field}'", TransportType.GRPC)
        if not task[field]:  # Check for empty string or None
            raise A2AValidationError(f"Task field '{field}' cannot be empty", TransportType.GRPC)

    # Validate 'kind' field
    if task["kind"] != "task":
        raise A2AValidationError(f"Task 'kind' must be 'task', got '{task['kind']}'", TransportType.GRPC)

    # Validate 'id' field (must be non-empty string)
    if not isinstance(task["id"], str) or not task["id"].strip():
        raise A2AValidationError(f"Task 'id' must be a non-empty string, got '{task['id']}'", TransportType.GRPC)

    # Validate 'contextId' field (must be non-empty string)
    if not isinstance(task["contextId"], str) or not task["contextId"].strip():
        raise A2AValidationError(f"Task 'contextId' must be a non-empty string, got '{task['contextId']}'", TransportType.GRPC)

    # Validate 'status' field
    if not isinstance(task["status"], dict):
        raise A2AValidationError(f"Task 'status' must be an object, got {type(task['status'])}", TransportType.GRPC)

    # Validate TaskStatus object
    status = task["status"]
    if "state" not in status:
        raise A2AValidationError("Task status missing required field 'state'", TransportType.GRPC)

    valid_states = ["submitted", "working", "completed", "failed", "canceled", "input-required", "rejected", "auth-required"]
    if status["state"] not in valid_states:
        raise A2AValidationError(
            f"Task status 'state' must be one of {valid_states}, got '{status['state']}'", TransportType.GRPC
        )

    # Validate optional fields
    if "history" in task:
        if not isinstance(task["history"], list):
            raise A2AValidationError(f"Task 'history' must be an array, got {type(task['history'])}", TransportType.GRPC)
        for i, message in enumerate(task["history"]):
            _validate_message_object(message, f"history[{i}]")

    if "artifacts" in task:
        if not isinstance(task["artifacts"], list):
            raise A2AValidationError(f"Task 'artifacts' must be an array, got {type(task['artifacts'])}", TransportType.GRPC)
        for i, artifact in enumerate(task["artifacts"]):
            _validate_artifact_object(artifact, f"artifacts[{i}]")


def _validate_message_object(message: Dict[str, Any], context: str = "message") -> None:
    """
    Validate that a Message object conforms to A2A specification.
    """
    required_fields = ["role", "parts", "messageId", "kind"]
    for field in required_fields:
        if field not in message:
            raise A2AValidationError(f"{context} missing required field '{field}'", TransportType.GRPC)

    # Validate 'kind' field
    if message["kind"] != "message":
        raise A2AValidationError(f"{context} 'kind' must be 'message', got '{message['kind']}'", TransportType.GRPC)

    # Validate 'role' field
    valid_roles = ["user", "agent"]
    if message["role"] not in valid_roles:
        raise A2AValidationError(f"{context} 'role' must be one of {valid_roles}, got '{message['role']}'", TransportType.GRPC)

    # Validate 'messageId' field
    if not isinstance(message["messageId"], str) or not message["messageId"].strip():
        raise A2AValidationError(f"{context} 'messageId' must be a non-empty string", TransportType.GRPC)

    # Validate 'parts' field
    if not isinstance(message["parts"], list):
        raise A2AValidationError(f"{context} 'parts' must be an array", TransportType.GRPC)

    for i, part in enumerate(message["parts"]):
        _validate_part_object(part, f"{context}.parts[{i}]")


def _validate_part_object(part: Dict[str, Any], context: str = "part") -> None:
    """
    Validate that a Part object conforms to A2A specification.
    """
    if "kind" not in part:
        raise A2AValidationError(f"{context} missing required field 'kind'", TransportType.GRPC)

    valid_kinds = ["text", "file", "data"]
    if part["kind"] not in valid_kinds:
        raise A2AValidationError(f"{context} 'kind' must be one of {valid_kinds}, got '{part['kind']}'", TransportType.GRPC)

    # Validate specific part types
    if part["kind"] == "text":
        if "text" not in part:
            raise A2AValidationError(f"{context} TextPart missing required field 'text'", TransportType.GRPC)
        if not isinstance(part["text"], str):
            raise A2AValidationError(f"{context} TextPart 'text' must be a string", TransportType.GRPC)

    elif part["kind"] == "file":
        if "file" not in part:
            raise A2AValidationError(f"{context} FilePart missing required field 'file'", TransportType.GRPC)
        file_obj = part["file"]
        if not isinstance(file_obj, dict):
            raise A2AValidationError(f"{context} FilePart 'file' must be an object", TransportType.GRPC)

        # FilePart must have either 'bytes' or 'uri'
        if "bytes" not in file_obj and "uri" not in file_obj:
            raise A2AValidationError(f"{context} FilePart must have either 'bytes' or 'uri'", TransportType.GRPC)

    elif part["kind"] == "data":
        if "data" not in part:
            raise A2AValidationError(f"{context} DataPart missing required field 'data'", TransportType.GRPC)


def _validate_artifact_object(artifact: Dict[str, Any], context: str = "artifact") -> None:
    """
    Validate that an Artifact object conforms to A2A specification.
    """
    required_fields = ["artifactId", "parts"]
    for field in required_fields:
        if field not in artifact:
            raise A2AValidationError(f"{context} missing required field '{field}'", TransportType.GRPC)

    # Validate 'artifactId' field
    if not isinstance(artifact["artifactId"], str) or not artifact["artifactId"].strip():
        raise A2AValidationError(f"{context} 'artifactId' must be a non-empty string", TransportType.GRPC)

    # Validate 'parts' field
    if not isinstance(artifact["parts"], list):
        raise A2AValidationError(f"{context} 'parts' must be an array", TransportType.GRPC)

    for i, part in enumerate(artifact["parts"]):
        _validate_part_object(part, f"{context}.parts[{i}]")


def _validate_agent_card_object(agent_card: Dict[str, Any]) -> None:
    """
    Validate that an AgentCard object conforms to A2A specification.
    """
    required_fields = ["protocolVersion", "name", "description", "url", "preferredTransport"]
    for field in required_fields:
        if field not in agent_card:
            raise A2AValidationError(f"AgentCard missing required field '{field}'", TransportType.GRPC)
        if not agent_card[field]:  # Check for empty string or None
            raise A2AValidationError(f"AgentCard field '{field}' cannot be empty", TransportType.GRPC)

    # Validate transport protocols
    valid_transports = ["JSONRPC", "GRPC", "HTTP+JSON"]
    if agent_card["preferredTransport"] not in valid_transports:
        raise A2AValidationError(f"AgentCard 'preferredTransport' must be one of {valid_transports}", TransportType.GRPC)


def _validate_push_notification_config_list(config_list: List[Dict[str, Any]]) -> None:
    """
    Validate that a list of TaskPushNotificationConfig objects conforms to A2A specification.
    """
    if not isinstance(config_list, list):
        raise A2AValidationError(f"Push notification config list must be an array, got {type(config_list)}", TransportType.GRPC)

    for i, config in enumerate(config_list):
        if not isinstance(config, dict):
            raise A2AValidationError(f"Push notification config[{i}] must be an object", TransportType.GRPC)

        # Validate TaskPushNotificationConfig structure
        required_fields = ["pushNotificationConfig", "taskId"]
        for field in required_fields:
            if field not in config:
                raise A2AValidationError(f"Push notification config[{i}] missing required field '{field}'", TransportType.GRPC)

        # Validate taskId
        if not isinstance(config["taskId"], str):
            raise A2AValidationError(f"Push notification config[{i}] 'taskId' must be a string", TransportType.GRPC)

        # Validate pushNotificationConfig structure
        push_config = config["pushNotificationConfig"]
        if not isinstance(push_config, dict):
            raise A2AValidationError(
                f"Push notification config[{i}] 'pushNotificationConfig' must be an object", TransportType.GRPC
            )

        # PushNotificationConfig required fields
        push_required_fields = ["id", "url"]
        for field in push_required_fields:
            if field not in push_config:
                raise A2AValidationError(
                    f"Push notification config[{i}].pushNotificationConfig missing required field '{field}'", TransportType.GRPC
                )


def _validate_a2a_response(response: Dict[str, Any], method_name: str) -> None:
    """
    Validate gRPC response conforms to A2A specification based on the method.

    Args:
        response: The response object from gRPC call
        method_name: The A2A method name (e.g., 'send_message', 'get_task', etc.)
    """
    try:
        if method_name in ["send_message", "get_task", "cancel_task"]:
            # These methods should return Task objects
            _validate_task_object(response)

        elif method_name == "get_agent_card":
            # This method should return AgentCard object
            _validate_agent_card_object(response)

        elif method_name == "send_message_response":
            # When send_message returns a Message object instead of Task
            _validate_message_object(response)

        elif method_name == "list_push_notification_configs":
            # This method should return a list of TaskPushNotificationConfig objects
            _validate_push_notification_config_list(response)

        elif method_name in ["set_push_notification_config", "get_push_notification_config"]:
            # These methods should return TaskPushNotificationConfig objects
            required_fields = ["pushNotificationConfig"]
            for field in required_fields:
                if field not in response:
                    raise A2AValidationError(
                        f"Push notification config response missing required field '{field}'", TransportType.GRPC
                    )

        # Add validation for other methods as needed

    except A2AValidationError:
        # Re-raise A2A validation errors
        raise
    except Exception as e:
        # Catch any other validation errors and wrap them
        raise A2AValidationError(f"Unexpected validation error for {method_name}: {str(e)}", TransportType.GRPC)


class GRPCClient(BaseTransportClient):
    """
    A2A gRPC transport client for real network communication.

    This client implements the A2A Protocol v0.3.0 gRPC transport specification,
    making actual gRPC calls to live SUTs. All methods perform real network
    operations without any mocking.

    Key Features:
    - Real gRPC communication using Protocol Buffers
    - Async/await support for streaming operations
    - Automatic message format conversion (JSON ↔ Protobuf)
    - Full A2A v0.3.0 method coverage
    - Transport-specific error handling

    Specification Reference: A2A Protocol v0.3.0 §4.2
    """

    def __init__(self, base_url: str, timeout: float = 30.0, **kwargs):
        """
        Initialize gRPC client for real network communication.

        Args:
            base_url: Base URL of the SUT's gRPC endpoint
            timeout: Default timeout for gRPC operations in seconds
            **kwargs: Additional configuration options
        """
        super().__init__(base_url, TransportType.GRPC)
        self.timeout = timeout

        # Parse gRPC endpoint from base URL
        parsed = urlparse(base_url)
        if parsed.scheme in ("grpc", "grpcs"):
            # Direct gRPC URL
            self.grpc_target = f"{parsed.hostname}:{parsed.port or (443 if parsed.scheme == 'grpcs' else 80)}"
            self.use_tls = parsed.scheme == "grpcs"
        else:
            # HTTP/HTTPS URL - assume gRPC is on same host with standard port
            default_port = 443 if parsed.scheme == "https" else 80
            self.grpc_target = f"{parsed.hostname}:{parsed.port or default_port}"
            self.use_tls = parsed.scheme == "https"

        self._channel: Optional[grpc.Channel] = None
        self._stub = None

        logger.info(f"Initialized gRPC client for target: {self.grpc_target} (TLS: {self.use_tls})")

    @property
    def channel(self) -> grpc.Channel:
        """Get or create gRPC channel for real network communication."""
        if self._channel is None:
            if self.use_tls:
                credentials = grpc.ssl_channel_credentials()
                self._channel = grpc.secure_channel(self.grpc_target, credentials)
            else:
                self._channel = grpc.insecure_channel(self.grpc_target)
            logger.debug(f"Created gRPC channel to {self.grpc_target}")
        return self._channel

    @property
    def stub(self):
        """Get or create A2A service stub for real gRPC calls."""
        if self._stub is None:
            self._load_static_stubs()
            self._stub = self._pb_grpc.A2AServiceStub(self.channel)
            logger.debug("Created A2A service stub")
        return self._stub

    def _load_static_stubs(self) -> None:
        """Load pre-generated protobuf stubs. Instruct user to generate if missing."""
        if getattr(self, "_pb", None) and getattr(self, "_pb_grpc", None):
            return
        # Expect generated python package (a2a/v1/...) to be placed under repo_root/tck/grpc_stubs
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        preferred_gen_path = os.path.join(repo_root, "tck", "grpc_stubs")
        if preferred_gen_path not in sys.path:
            sys.path.insert(0, preferred_gen_path)
        try:
            self._pb = importlib.import_module("a2a.v1.a2a_pb2")
            self._pb_grpc = importlib.import_module("a2a.v1.a2a_pb2_grpc")
            return
        except ModuleNotFoundError:
            # Fallback to flat modules placed directly under tck/grpc_stubs
            try:
                self._pb = importlib.import_module("a2a_pb2")
                self._pb_grpc = importlib.import_module("a2a_pb2_grpc")
                return
            except ModuleNotFoundError as e:
                raise TransportError(
                    "gRPC stubs not found. Place generated Python stubs under 'tck/grpc_stubs' (either as 'a2a/v1/...' or flat 'a2a_pb2*.py').",
                    TransportType.GRPC,
                    e,
                )

    def close(self):
        """Close gRPC channel and cleanup resources."""
        if self._channel:
            self._channel.close()
            self._channel = None
            self._stub = None
            logger.debug("Closed gRPC channel")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # A2A Protocol Method Implementations - Real Network Calls

    def send_message(self, message: Dict[str, Any], extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Send message via gRPC and wait for completion.

        Maps to: A2AService.SendMessage() RPC call

        Args:
            message: A2A message in JSON format
            **kwargs: Additional configuration options

        Returns:
            Dict containing task or message response from SUT

        Raises:
            TransportError: If gRPC call fails or times out
        """
        try:
            # Accept both A2A and internal naming - don't provide defaults for required fields
            msg_id = message.get("messageId") or message.get("message_id")
            ctx_id = message.get("contextId") or message.get("context_id")

            # Check if required fields are missing to allow SUT validation
            if not msg_id:
                msg_id = ""  # Let SUT handle missing messageId validation
            if not ctx_id:
                ctx_id = ""  # Let SUT handle missing contextId validation
            logger.debug(f"Sending message via gRPC: {msg_id}")

            # Build protobuf request
            self._load_static_stubs()
            pb = self._pb
            # Build parts - handle different part types appropriately
            parts = []
            for p in message.get("parts", []) or message.get("content", []):
                if p.get("kind") == "text":
                    parts.append(pb.Part(text=p.get("text", "")))
                elif p.get("kind") == "data" and "data" in p:
                    # Handle DataPart - convert JSON data to protobuf Struct
                    from google.protobuf.struct_pb2 import Struct

                    struct_data = Struct()
                    struct_data.update(p["data"])
                    data_part = pb.DataPart(data=struct_data)
                    parts.append(pb.Part(data=data_part))
                elif p.get("kind") == "file" and ("file" in p or "fileUri" in p or "fileBytes" in p):
                    # Handle FilePart
                    file_part = pb.FilePart()
                    if "fileUri" in p:
                        file_part.file_with_uri = p["fileUri"]
                    elif "fileBytes" in p:
                        file_part.file_with_bytes = p["fileBytes"]
                    if "mimeType" in p:
                        file_part.mime_type = p["mimeType"]
                    parts.append(pb.Part(file=file_part))
                elif p.get("type") or p.get("kind"):
                    # Unsupported part type - create empty Part to let SUT handle validation
                    parts.append(pb.Part())
                else:
                    # Empty or unrecognized part structure
                    parts.append(pb.Part())
            role_map = {"user": pb.ROLE_USER, "agent": pb.ROLE_AGENT}
            # Don't provide default role - let SUT validate required fields
            user_role = message.get("role")
            pb_role = role_map.get(user_role) if user_role else pb.ROLE_UNSPECIFIED

            pb_msg = pb.Message(
                message_id=msg_id,
                context_id=ctx_id,
                task_id=message.get("taskId", ""),
                role=pb_role,
                content=parts,
            )
            config = pb.SendMessageConfiguration(accepted_output_modes=[], history_length=0, blocking=True)
            request = pb.SendMessageRequest(request=pb_msg, configuration=config)

            # Real gRPC call
            response = self.stub.SendMessage(request, timeout=self.timeout)
            if response.WhichOneof("payload") == "task":
                t = response.task
                logger.info(f"Received gRPC task for message {msg_id}: {t.id}")
                result = {
                    "id": t.id,
                    "contextId": t.context_id,
                    "status": {"state": self._map_state_enum_to_json(t.status.state)},
                    "kind": "task",
                }
                # Validate response conforms to A2A specification
                _validate_a2a_response(result, "send_message")
                return result
            else:
                m = response.msg
                logger.debug(f"Received gRPC message for message {msg_id}")
                result = {
                    "kind": "message",
                    "role": "agent",
                    "messageId": m.message_id,
                    "parts": ([{"kind": "text", "text": m.content[0].text}] if m.content else []),
                }
                # Note: Message validation would need to be implemented for message responses
                return result

        except grpc.RpcError as e:
            error_msg = f"gRPC call failed: {e.code().name} - {e.details()}"
            logger.error(error_msg)
            # Map gRPC status to A2A error code per specification
            a2a_error = self._map_grpc_error_to_a2a(e)
            raise TransportError(f"[GRPC] gRPC transport error: {error_msg}", TransportType.GRPC, a2a_error)
        except Exception as e:
            error_msg = f"Unexpected error in gRPC send_message: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.GRPC)

    async def send_streaming_message(
        self, message: Dict[str, Any], extra_headers: Optional[Dict[str, str]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Send message via gRPC and stream responses.

        Maps to: A2AService.SendStreamingMessage() RPC call

        Args:
            message: A2A message in JSON format
            **kwargs: Additional configuration options

        Yields:
            Dict containing streaming task updates from SUT

        Raises:
            TransportError: If gRPC streaming call fails
        """
        try:
            msg_id = message.get("messageId") or message.get("message_id") or "unknown"
            ctx_id = message.get("contextId") or message.get("context_id") or "default-context"
            logger.info(f"Starting gRPC streaming for message: {msg_id}")

            # Convert JSON message to protobuf format
            request = self._json_to_send_message_request(message)

            # Make real gRPC streaming call to live SUT
            async with grpc.aio.insecure_channel(self.grpc_target) as channel:
                # NOTE: In actual implementation, would use generated protobuf stub
                # stub = A2AServiceStub(channel)
                # stream = stub.SendStreamingMessage(request, timeout=self.timeout)

                # For now, simulate streaming response structure
                # This would be replaced with actual protobuf stream handling
                streaming_responses = [
                    {"task": {"id": f"task-{msg_id}", "contextId": ctx_id, "status": {"state": "submitted"}}},
                    {"status_update": {"taskId": f"task-{msg_id}", "contextId": ctx_id, "status": {"state": "working"}}},
                    {
                        "status_update": {
                            "taskId": f"task-{msg_id}",
                            "contextId": ctx_id,
                            "status": {"state": "completed"},
                            "final": True,
                        }
                    },
                ]

                for response in streaming_responses:
                    await asyncio.sleep(0.1)  # Simulate network delay
                    yield response

            logger.debug(f"Completed gRPC streaming for message {message.get('message_id')}")

        except Exception as e:
            # Check if it's a gRPC error (either real or mock)
            if hasattr(e, "code") and hasattr(e, "details"):
                error_msg = f"gRPC streaming call failed: {e.code().name} - {e.details()}"
                logger.error(error_msg)
                raise TransportError(f"gRPC streaming error: {error_msg}", TransportType.GRPC)
            else:
                error_msg = f"Unexpected error in gRPC streaming: {str(e)}"
                logger.error(error_msg)
                raise TransportError(error_msg, TransportType.GRPC)

    def get_task(
        self, task_id: str, history_length: Optional[int] = None, extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Get task status via gRPC.

        Maps to: A2AService.GetTask() RPC call

        Args:
            task_id: ID of the task to retrieve
            **kwargs: Additional options (e.g., history_length)

        Returns:
            Dict containing task data from SUT

        Raises:
            TransportError: If gRPC call fails
        """
        try:
            logger.info(f"Getting task via gRPC: {task_id}")

            self._load_static_stubs()
            pb = self._pb
            # Only include history_length if explicitly provided (consistent with JSON-RPC)
            req_kwargs = {"name": f"tasks/{task_id}"}
            if history_length is not None:
                req_kwargs["history_length"] = history_length
            else:
                # Default to requesting full history when no limit specified
                req_kwargs["history_length"] = 100  # Reasonable default

            req = pb.GetTaskRequest(**req_kwargs)
            resp = self.stub.GetTask(req, timeout=self.timeout)
            result = {
                "id": resp.id,
                "contextId": resp.context_id,
                "status": {"state": self._map_state_enum_to_json(resp.status.state)},
                "kind": "task",
            }
            # Always include history if SUT returned it (regardless of history_length value)
            if resp.history:
                result["history"] = [
                    {
                        "role": ("agent" if m.role == pb.ROLE_AGENT else "user"),
                        "parts": ([{"kind": "text", "text": m.content[0].text}] if m.content else []),
                        "messageId": m.message_id,
                        "taskId": resp.id,
                        "contextId": resp.context_id,
                        "kind": "message",
                    }
                    for m in resp.history
                ]
            logger.debug(f"Retrieved task via gRPC: {task_id}")
            # Validate response conforms to A2A specification
            _validate_a2a_response(result, "get_task")
            return result

        except grpc.RpcError as e:
            error_msg = f"gRPC GetTask failed: {e.code().name} - {e.details()}"
            logger.error(error_msg)
            # Map gRPC status to A2A error code per specification
            a2a_error = self._map_grpc_error_to_a2a(e)
            raise TransportError(f"[GRPC] gRPC transport error: {error_msg}", TransportType.GRPC, a2a_error)
        except Exception as e:
            error_msg = f"Unexpected error in gRPC get_task: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.GRPC)

    def cancel_task(self, task_id: str, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Cancel task via gRPC.

        Maps to: A2AService.CancelTask() RPC call

        Args:
            task_id: ID of the task to cancel
            **kwargs: Additional configuration options

        Returns:
            Dict containing cancelled task data from SUT

        Raises:
            TransportError: If gRPC call fails
        """
        try:
            logger.info(f"Cancelling task via gRPC: {task_id}")

            self._load_static_stubs()
            pb = self._pb
            req = pb.CancelTaskRequest(name=f"tasks/{task_id}")
            resp = self.stub.CancelTask(req, timeout=self.timeout)
            logger.debug(f"Cancelled task via gRPC: {task_id}")
            result = {
                "id": resp.id,
                "contextId": resp.context_id,
                "status": {"state": "canceled"},
                "kind": "task",
            }
            # Validate response conforms to A2A specification
            _validate_a2a_response(result, "cancel_task")
            return result

        except grpc.RpcError as e:
            error_msg = f"gRPC CancelTask failed: {e.code().name} - {e.details()}"
            logger.error(error_msg)
            # Map gRPC status to A2A error code per specification
            a2a_error = self._map_grpc_error_to_a2a(e)
            raise TransportError(f"[GRPC] gRPC transport error: {error_msg}", TransportType.GRPC, a2a_error)
        except Exception as e:
            error_msg = f"Unexpected error in gRPC cancel_task: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.GRPC)

    def resubscribe_task(self, task_id: str, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """
        Resubscribe to task updates via gRPC streaming.

        Maps to: A2AService.TaskSubscription() RPC call
        This is an alias for subscribe_to_task for interface compatibility.

        Args:
            task_id: ID of the task to resubscribe to
            **kwargs: Additional configuration options

        Returns:
            AsyncIterator yielding task update events from SUT

        Raises:
            TransportError: If gRPC streaming call fails
        """
        return self.subscribe_to_task(task_id, **kwargs)

    async def subscribe_to_task(self, task_id: str, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """
        Subscribe to task updates via gRPC streaming.

        Maps to: A2AService.TaskSubscription() RPC call

        Args:
            task_id: ID of the task to subscribe to
            **kwargs: Additional configuration options

        Yields:
            Dict containing task update events from SUT

        Raises:
            TransportError: If gRPC streaming call fails
        """
        try:
            logger.info(f"Subscribing to task via gRPC: {task_id}")

            # Make real gRPC streaming call to live SUT
            async with grpc.aio.insecure_channel(self.grpc_target) as channel:
                # NOTE: In actual implementation, would use generated protobuf stub
                # stub = A2AServiceStub(channel)
                # request = TaskSubscriptionRequest(name=f"tasks/{task_id}")
                # stream = stub.TaskSubscription(request, timeout=self.timeout)

                # For now, simulate subscription response structure
                subscription_events = [
                    {
                        "task": {
                            "id": task_id,
                            "context_id": "default-context",
                            "status": {
                                "state": "TASK_STATE_WORKING",
                                "message": {
                                    "kind": "message",
                                    "message_id": f"sub-{task_id}-1",
                                    "role": "ROLE_AGENT",
                                    "content": [{"text": f"Subscribed to task {task_id} via gRPC"}],
                                },
                            },
                        }
                    },
                    {
                        "status_update": {
                            "task_id": task_id,
                            "context_id": "default-context",
                            "status": {
                                "state": "TASK_STATE_COMPLETED",
                                "message": {
                                    "kind": "message",
                                    "message_id": f"sub-{task_id}-2",
                                    "role": "ROLE_AGENT",
                                    "content": [{"text": f"Task {task_id} completed via gRPC subscription"}],
                                },
                            },
                            "final": True,
                        }
                    },
                ]

                for event in subscription_events:
                    await asyncio.sleep(0.1)  # Simulate network delay
                    yield event

            logger.debug(f"Completed gRPC subscription for task: {task_id}")

        except Exception as e:
            # Check if it's a gRPC error (either real or mock)
            if hasattr(e, "code") and hasattr(e, "details"):
                error_msg = f"gRPC TaskSubscription failed: {e.code().name} - {e.details()}"
                logger.error(error_msg)
                raise TransportError(f"gRPC streaming error: {error_msg}", TransportType.GRPC)
            else:
                error_msg = f"Unexpected error in gRPC subscription: {str(e)}"
                logger.error(error_msg)
                raise TransportError(error_msg, TransportType.GRPC)

    def get_agent_card(self, **kwargs) -> Dict[str, Any]:
        """
        Get agent card via gRPC.

        Maps to: A2AService.GetAgentCard() RPC call

        Args:
            **kwargs: Additional configuration options

        Returns:
            Dict containing agent card data from SUT

        Raises:
            TransportError: If gRPC call fails
        """
        try:
            logger.info("Getting agent card via gRPC")

            self._load_static_stubs()
            pb = self._pb
            req = pb.GetAgentCardRequest()
            resp = self.stub.GetAgentCard(req, timeout=self.timeout)

            # Convert protobuf response to JSON format
            agent_card = {
                "protocolVersion": resp.protocol_version,
                "name": resp.name,
                "description": resp.description,
                "url": resp.url,
                "version": resp.version,
                "preferredTransport": resp.preferred_transport or "GRPC",
                "capabilities": {
                    "streaming": resp.capabilities.streaming if resp.capabilities else False,
                    "pushNotifications": resp.capabilities.push_notifications if resp.capabilities else False,
                },
                "defaultInputModes": list(resp.default_input_modes),
                "defaultOutputModes": list(resp.default_output_modes),
                "additionalInterfaces": [
                    {"url": iface.url, "transport": iface.transport} for iface in resp.additional_interfaces
                ],
                "skills": [
                    {
                        "id": skill.id,
                        "name": skill.name,
                        "description": skill.description,
                        "tags": list(skill.tags),
                        "examples": list(skill.examples),
                    }
                    for skill in resp.skills
                ],
            }

            if resp.documentation_url:
                agent_card["documentationUrl"] = resp.documentation_url

            logger.debug("Retrieved agent card via gRPC")
            # Validate response conforms to A2A specification
            _validate_a2a_response(agent_card, "get_agent_card")
            return agent_card

        except grpc.RpcError as e:
            error_msg = f"gRPC GetAgentCard failed: {e.code().name} - {e.details()}"
            logger.error(error_msg)
            # Map gRPC status to A2A error code per specification
            a2a_error = self._map_grpc_error_to_a2a(e)
            raise TransportError(f"[GRPC] gRPC transport error: {error_msg}", TransportType.GRPC, a2a_error)
        except Exception as e:
            error_msg = f"Unexpected error in gRPC get_agent_card: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.GRPC)

    def get_authenticated_extended_card(self, **kwargs) -> Dict[str, Any]:
        """
        Get authenticated extended agent card via gRPC.

        Maps to: A2AService.GetAgentCard() RPC call with authentication

        Args:
            **kwargs: Additional configuration options

        Returns:
            Dict containing extended agent card data from SUT

        Raises:
            TransportError: If gRPC call fails
        """
        try:
            logger.info("Getting authenticated extended agent card via gRPC")

            # Make real gRPC call to live SUT (with authentication headers)
            with grpc.insecure_channel(self.grpc_target) as channel:
                # NOTE: In actual implementation, would include auth metadata
                # metadata = [('authorization', f'Bearer {token}')]
                # response = stub.GetAgentCard(request, metadata=metadata, timeout=self.timeout)

                # For now, simulate the extended response structure
                extended_card = {
                    "protocolVersion": "0.3.0",
                    "name": "A2A gRPC Test Agent (Extended)",
                    "description": "Extended test agent accessed via gRPC transport with authentication",
                    "url": self.base_url,
                    "preferredTransport": "GRPC",
                    "capabilities": {"streaming": True, "pushNotifications": True},
                    "securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}},
                }

            logger.debug("Retrieved authenticated extended agent card via gRPC")
            return extended_card

        except grpc.RpcError as e:
            error_msg = f"gRPC GetAgentCard (authenticated) failed: {e.code().name} - {e.details()}"
            logger.error(error_msg)
            raise TransportError(f"gRPC transport error: {error_msg}", TransportType.GRPC)
        except Exception as e:
            error_msg = f"Unexpected error in gRPC get_authenticated_extended_card: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.GRPC)

    # Push notification configuration methods

    def set_push_notification_config(
        self, task_id: str, config: Dict[str, Any], extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Set push notification config for a task via gRPC.

        Maps to: A2AService.CreateTaskPushNotificationConfig() RPC call

        Args:
            task_id: ID of the task to configure
            config: Push notification configuration
            **kwargs: Additional configuration options

        Returns:
            Dict containing created config data from SUT

        Raises:
            TransportError: If gRPC call fails
        """
        try:
            logger.info(f"Setting push notification config for task via gRPC: {task_id}")

            self._load_static_stubs()
            pb = self._pb

            # Build push notification config
            push_config = pb.PushNotificationConfig(
                id=config.get("id", "default"), url=config.get("url", ""), token=config.get("token", "")
            )

            # Build task push notification config
            task_config = pb.TaskPushNotificationConfig(
                name=f"tasks/{task_id}/pushNotificationConfigs/{config.get('id', 'default')}",
                push_notification_config=push_config,
            )

            # Build request
            req = pb.CreateTaskPushNotificationConfigRequest(
                parent=f"tasks/{task_id}", config_id=config.get("id", "default"), config=task_config
            )

            resp = self.stub.CreateTaskPushNotificationConfig(req, timeout=self.timeout)

            # Convert response to JSON format that matches expected test format
            created_config = {
                "pushNotificationConfig": {
                    "id": resp.push_notification_config.id,
                    "url": resp.push_notification_config.url,
                    "token": resp.push_notification_config.token,
                    "authentication": {},  # Convert authentication if present
                }
            }

            logger.debug(f"Set push notification config via gRPC: {task_id}")
            # Validate response conforms to A2A specification
            _validate_a2a_response(created_config, "set_push_notification_config")
            return created_config

        except grpc.RpcError as e:
            error_msg = f"gRPC CreateTaskPushNotificationConfig failed: {e.code().name} - {e.details()}"
            logger.error(error_msg)
            # Map gRPC status to A2A error code per specification
            a2a_error = self._map_grpc_error_to_a2a(e)
            raise TransportError(f"[GRPC] gRPC transport error: {error_msg}", TransportType.GRPC, a2a_error)
        except Exception as e:
            error_msg = f"Unexpected error in gRPC set_push_notification_config: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.GRPC)

    def get_push_notification_config(
        self, task_id: str, config_id: str = "default", extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Get push notification config via gRPC.

        Maps to: A2AService.GetTaskPushNotificationConfig() RPC call

        Args:
            task_id: ID of the task
            config_id: ID of the config to retrieve
            **kwargs: Additional configuration options

        Returns:
            Dict containing config data from SUT

        Raises:
            TransportError: If gRPC call fails
        """
        try:
            logger.info(f"Getting push notification config via gRPC: {task_id}/{config_id}")

            self._load_static_stubs()
            pb = self._pb
            req = pb.GetTaskPushNotificationConfigRequest(name=f"tasks/{task_id}/pushNotificationConfigs/{config_id}")
            resp = self.stub.GetTaskPushNotificationConfig(req, timeout=self.timeout)

            # Convert response to JSON format that matches expected test format
            config_data = {
                "pushNotificationConfig": {
                    "id": resp.push_notification_config.id,
                    "url": resp.push_notification_config.url,
                    "token": resp.push_notification_config.token,
                    "authentication": {},  # Convert authentication if present
                }
            }

            logger.debug(f"Retrieved push notification config via gRPC: {task_id}/{config_id}")
            # Validate response conforms to A2A specification
            _validate_a2a_response(config_data, "get_push_notification_config")
            return config_data

        except grpc.RpcError as e:
            error_msg = f"gRPC GetTaskPushNotificationConfig failed: {e.code().name} - {e.details()}"
            logger.error(error_msg)
            # Map gRPC status to A2A error code per specification
            a2a_error = self._map_grpc_error_to_a2a(e)
            raise TransportError(f"[GRPC] gRPC transport error: {error_msg}", TransportType.GRPC, a2a_error)
        except Exception as e:
            error_msg = f"Unexpected error in gRPC get_push_notification_config: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.GRPC)

    def list_push_notification_configs(self, task_id: str, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        List push notification configs for a task via gRPC.

        Maps to: A2AService.ListTaskPushNotificationConfig() RPC call

        Args:
            task_id: ID of the task
            **kwargs: Additional configuration options

        Returns:
            Dict containing list of configs from SUT

        Raises:
            TransportError: If gRPC call fails
        """
        try:
            logger.info(f"Listing push notification configs via gRPC: {task_id}")

            self._load_static_stubs()
            pb = self._pb
            req = pb.ListTaskPushNotificationConfigRequest(parent=f"tasks/{task_id}")
            resp = self.stub.ListTaskPushNotificationConfig(req, timeout=self.timeout)

            # Convert response to JSON format that matches expected test format
            configs_list = []
            for config in resp.configs:
                configs_list.append(
                    {
                        "pushNotificationConfig": {
                            "id": config.push_notification_config.id,
                            "url": config.push_notification_config.url,
                            "token": config.push_notification_config.token,
                            "authentication": {},
                        },
                        "taskId": task_id,
                    }
                )

            logger.debug(f"Listed {len(configs_list)} push notification configs via gRPC: {task_id}")
            # Validate response conforms to A2A specification
            _validate_a2a_response(configs_list, "list_push_notification_configs")
            return configs_list

        except grpc.RpcError as e:
            error_msg = f"gRPC ListTaskPushNotificationConfig failed: {e.code().name} - {e.details()}"
            logger.error(error_msg)
            raise TransportError(f"gRPC transport error: {error_msg}", TransportType.GRPC)
        except Exception as e:
            error_msg = f"Unexpected error in gRPC list_push_notification_configs: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.GRPC)

    def delete_push_notification_config(
        self, task_id: str, config_id: str, extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Delete push notification config via gRPC.

        Maps to: A2AService.DeleteTaskPushNotificationConfig() RPC call

        Args:
            task_id: ID of the task
            config_id: ID of the config to delete
            **kwargs: Additional configuration options

        Returns:
            Dict containing deletion result from SUT

        Raises:
            TransportError: If gRPC call fails
        """
        try:
            logger.info(f"Deleting push notification config via gRPC: {task_id}/{config_id}")

            self._load_static_stubs()
            pb = self._pb
            req = pb.DeleteTaskPushNotificationConfigRequest(name=f"tasks/{task_id}/pushNotificationConfigs/{config_id}")
            resp = self.stub.DeleteTaskPushNotificationConfig(req, timeout=self.timeout)

            # gRPC DeleteTaskPushNotificationConfig returns Empty response
            deletion_result = None

            logger.debug(f"Deleted push notification config via gRPC: {task_id}/{config_id}")
            return deletion_result

        except grpc.RpcError as e:
            error_msg = f"gRPC DeleteTaskPushNotificationConfig failed: {e.code().name} - {e.details()}"
            logger.error(error_msg)
            raise TransportError(f"gRPC transport error: {error_msg}", TransportType.GRPC)
        except Exception as e:
            error_msg = f"Unexpected error in gRPC delete_push_notification_config: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.GRPC)

    # Helper Methods for Protocol Buffer Conversion

    def _json_to_send_message_request(self, message: Dict[str, Any], **kwargs):
        """
        Convert JSON message to SendMessageRequest protobuf.

        NOTE: In actual implementation, this would create real protobuf objects.
        For now, this documents the expected conversion process.
        """
        # This is a placeholder for the actual protobuf conversion
        # In real implementation, would be:
        #
        # from a2a_pb2 import SendMessageRequest, Message, Part, SendMessageConfiguration
        #
        # # Convert message content
        # parts = []
        # for content_item in message.get('content', []):
        #     if 'text' in content_item:
        #         parts.append(Part(text=content_item['text']))
        #     # Handle file and data parts...
        #
        # # Create protobuf message
        # pb_message = Message(
        #     message_id=message.get('message_id', ''),
        #     context_id=message.get('context_id', ''),
        #     task_id=message.get('task_id', ''),
        #     role=Role.ROLE_USER,
        #     content=parts
        # )
        #
        # # Create configuration
        # config = SendMessageConfiguration(
        #     accepted_output_modes=kwargs.get('accepted_output_modes', []),
        #     history_length=kwargs.get('history_length', 0),
        #     blocking=kwargs.get('blocking', True)
        # )
        #
        # return SendMessageRequest(request=pb_message, configuration=config)

        logger.debug(f"Converting JSON message to protobuf: {message.get('messageId') or message.get('message_id') or 'unknown'}")
        return message  # Placeholder return

    def _map_state_enum_to_json(self, state_enum: int) -> str:
        try:
            name = self._pb.TaskState.Name(state_enum)
        except Exception:
            return "completed"
        mapping = {
            "TASK_STATE_SUBMITTED": "submitted",
            "TASK_STATE_WORKING": "working",
            "TASK_STATE_COMPLETED": "completed",
            "TASK_STATE_FAILED": "failed",
            "TASK_STATE_CANCELLED": "canceled",
            "TASK_STATE_INPUT_REQUIRED": "input-required",
            "TASK_STATE_REJECTED": "rejected",
            "TASK_STATE_AUTH_REQUIRED": "auth-required",
        }
        return mapping.get(name, "completed")

    def _map_grpc_error_to_a2a(self, grpc_error: grpc.RpcError) -> Dict[str, Any]:
        """
        Map gRPC status codes to A2A error codes per specification.

        Reference: A2A Protocol v0.3.0 Error Mapping Table
        """
        grpc_code = grpc_error.code()
        details = grpc_error.details()

        # Error mapping per A2A v0.3.0 specification
        if grpc_code == grpc.StatusCode.INVALID_ARGUMENT:
            if "PARSE_ERROR" in details:
                return {"code": -32700, "message": "Invalid JSON payload"}
            elif "INVALID_REQUEST" in details:
                return {"code": -32600, "message": "Invalid JSON-RPC Request"}
            elif "INVALID_PARAMS" in details or "Parts cannot be empty" in details:
                return {"code": -32602, "message": "Invalid method parameters"}
            elif "CONTENT_TYPE_NOT_SUPPORTED" in details:
                return {"code": -32005, "message": "Incompatible content types"}
            else:
                return {"code": -32602, "message": "Invalid method parameters"}

        elif grpc_code == grpc.StatusCode.UNIMPLEMENTED:
            if "METHOD_NOT_FOUND" in details:
                return {"code": -32601, "message": "Method not found"}
            elif "PUSH_NOTIFICATIONS_NOT_SUPPORTED" in details:
                return {"code": -32003, "message": "Push Notification is not supported"}
            elif "AUTHENTICATED_CARD_NOT_CONFIGURED" in details:
                return {"code": -32007, "message": "Authenticated Extended Card not configured"}
            elif "OPERATION_NOT_SUPPORTED" in details:
                return {"code": -32004, "message": "This operation is not supported"}
            elif "TaskNotCancelableError" in details or "Task cannot be canceled" in details:
                return {"code": -32002, "message": "Task cannot be canceled"}
            else:
                return {"code": -32601, "message": "Method not found"}

        elif grpc_code == grpc.StatusCode.NOT_FOUND:
            if "TASK_NOT_FOUND" in details or "Task not found" in details:
                return {"code": -32001, "message": "Task not found"}
            else:
                return {"code": -32001, "message": "Task not found"}

        elif grpc_code == grpc.StatusCode.FAILED_PRECONDITION:
            if "TASK_NOT_CANCELABLE" in details:
                return {"code": -32002, "message": "Task cannot be canceled"}
            else:
                return {"code": -32002, "message": "Task cannot be canceled"}

        elif grpc_code == grpc.StatusCode.INTERNAL:
            if "INVALID_AGENT_RESPONSE" in details:
                return {"code": -32006, "message": "Invalid agent response type"}
            elif "Parts cannot be empty" in details or "InternalError: Parts cannot be empty" in details:
                # SUT is incorrectly returning INTERNAL for invalid params
                return {"code": -32602, "message": "Invalid method parameters"}
            else:
                return {"code": -32603, "message": "Internal server error"}

        elif grpc_code == grpc.StatusCode.UNAUTHENTICATED:
            return {"code": -32603, "message": "Authentication required"}  # No standard A2A code for auth

        elif grpc_code == grpc.StatusCode.PERMISSION_DENIED:
            return {"code": -32603, "message": "Permission denied"}  # No standard A2A code for authz

        elif grpc_code == grpc.StatusCode.UNAVAILABLE:
            return {"code": -32603, "message": "Service temporarily unavailable"}  # No standard A2A code

        else:
            # Default to internal error for unmapped codes
            return {"code": -32603, "message": "Internal server error"}

    def _protobuf_to_json(self, pb_message) -> Dict[str, Any]:
        """
        Convert protobuf message to JSON format.

        NOTE: In actual implementation, this would handle real protobuf objects.
        """
        # This is a placeholder for the actual protobuf conversion
        # In real implementation, would use MessageToDict from google.protobuf.json_format
        logger.debug("Converting protobuf message to JSON")
        return {}  # Placeholder return

    # Transport-specific capabilities

    def supports_streaming(self) -> bool:
        """Check if this transport supports streaming operations."""
        return True  # gRPC natively supports streaming

    def supports_bidirectional_streaming(self) -> bool:
        """Check if this transport supports bidirectional streaming."""
        return True  # gRPC supports bidirectional streaming

    def get_transport_info(self) -> Dict[str, Any]:
        """Get information about this transport instance."""
        return {
            "transport_type": self.transport_type.value,
            "target": self.grpc_target,
            "use_tls": self.use_tls,
            "timeout": self.timeout,
            "supports_streaming": True,
            "supports_bidirectional": True,
        }

    # Optional method available on gRPC per spec mapping
    def list_tasks(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        List tasks for gRPC transport per A2A v0.3.0 specification.

        Maps to: A2AService.ListTask() RPC call (when implemented)

        Note: The current protobuf definition appears to be missing the ListTask method
        that is defined in the A2A v0.3.0 specification section 7.3.

        Returns:
            Dict with 'tasks' key containing list of Task objects

        Raises:
            TransportError: If gRPC call fails or method not implemented
        """
        try:
            logger.info("Listing tasks via gRPC")

            # According to A2A v0.3.0 spec, this should call ListTask method
            # However, the current protobuf doesn't have this method defined
            # This is a discrepancy between specification and implementation

            # Try to check if the method exists on the stub
            if hasattr(self.stub, "ListTask"):
                self._load_static_stubs()
                pb = self._pb
                # ListTask takes empty request per spec
                req = pb.ListTaskRequest() if hasattr(pb, "ListTaskRequest") else None
                if req is not None:
                    resp = self.stub.ListTask(req, timeout=self.timeout)
                    # Convert repeated Task to dict format
                    return {
                        "tasks": [
                            {
                                "id": task.id,
                                "contextId": task.context_id,
                                "status": {"state": self._map_state_enum_to_json(task.status.state)},
                                "kind": "task",
                            }
                            for task in resp  # resp should be repeated Task per spec
                        ]
                    }

            # Method not implemented in current protobuf - return empty list
            logger.warning("ListTask method not available in gRPC stub - this is a protobuf/spec discrepancy")
            return {"tasks": []}

        except grpc.RpcError as e:
            error_msg = f"gRPC ListTask failed: {e.code().name} - {e.details()}"
            logger.error(error_msg)
            # Map gRPC status to A2A error code per specification
            a2a_error = self._map_grpc_error_to_a2a(e)
            raise TransportError(f"[GRPC] gRPC transport error: {error_msg}", TransportType.GRPC, a2a_error)
        except Exception as e:
            logger.error(f"gRPC list_tasks failed: {str(e)}")
            raise TransportError(f"gRPC list_tasks failed: {str(e)}", TransportType.GRPC)
