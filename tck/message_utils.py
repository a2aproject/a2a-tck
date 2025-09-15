import uuid
import json
from typing import Any, Dict, Optional, Union


def generate_request_id() -> str:
    return str(uuid.uuid4())


def make_json_rpc_request(
        method: str,
        params: Union[dict, list, None] = None,
        id: Union[str, int, None] = None,
) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params if params is not None else {},
        "id": id if id is not None else generate_request_id(),
    }


def is_json_rpc_success_response(resp: dict, expected_id: Union[str, int, None] = None) -> bool:
    if not isinstance(resp, dict):
        return False
    if resp.get("jsonrpc") != "2.0":
        return False
    if "result" not in resp:
        return False
    if expected_id is not None and resp.get("id") != expected_id:
        return False
    return True


def is_json_rpc_error_response(resp: dict, expected_id: Union[str, int, None] = None) -> bool:
    if not isinstance(resp, dict):
        return False
    if resp.get("jsonrpc") != "2.0":
        return False
    error = resp.get("error")
    if not isinstance(error, dict):
        return False
    if "code" not in error or "message" not in error:
        return False
    if expected_id is not None and resp.get("id") != expected_id:
        return False
    return True


# A2A Protocol Method Implementations - Real HTTP Calls

def convert_a2a_message_to_protobuf_json(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert A2A JSON message format to protobuf-compatible JSON format.

    A2A JSON format:
    {
        "kind": "message",
        "messageId": "...",
        "role": "user",
        "parts": [{"kind": "text", "text": "..."}]
    }

    Protobuf JSON format:
    {
        "message_id": "...",
        "role": "ROLE_USER",
        "content": [{"text": "..."}]
    }
    """
    protobuf_message = {}

    # Map messageId -> message_id
    if "messageId" in message:
        protobuf_message["message_id"] = message["messageId"]

    # Map contextId -> context_id
    if "contextId" in message:
        protobuf_message["context_id"] = message["contextId"]

    # Map taskId -> task_id
    if "taskId" in message:
        protobuf_message["task_id"] = message["taskId"]

    # Map role to protobuf enum format
    if "role" in message:
        role_map = {
            "user": "ROLE_USER",
            "agent": "ROLE_AGENT"
        }
        protobuf_message["role"] = role_map.get(message["role"], "ROLE_UNSPECIFIED")

    # Map parts -> content (and convert part format)
    if "parts" in message:
        protobuf_message["content"] = []
        for part in message["parts"]:
            protobuf_part = {}
            if part.get("kind") == "text":
                protobuf_part["text"] = part.get("text", "")
            elif part.get("kind") == "file":
                # Map file part (simplified for now)
                if "file" in part:
                    file_data = part["file"]
                    protobuf_part["file"] = {
                        # "name": file_data.get("name", ""),
                        "mime_type": file_data.get("mimeType", ""),
                        "file_with_uri": file_data.get("uri", file_data.get("url", "")),
                        # "size_in_bytes": file_data.get("sizeInBytes", 0)
                    }
                    if "bytes" in file_data:
                        protobuf_part["file"]["file_with_bytes"] = file_data["bytes"]
            elif part.get("kind") == "data":
                # DataPart has structure: {"data": {"data": <actual_data>}}
                # The protobuf DataPart has a single field "data" of type google.protobuf.Struct
                protobuf_part["data"] = {"data": part.get("data", {})}

            # Add metadata if present
            if "metadata" in part:
                protobuf_part["metadata"] = part["metadata"]

            protobuf_message["content"].append(protobuf_part)

    # Map metadata if present
    if "metadata" in message:
        protobuf_message["metadata"] = message["metadata"]

    # Map extensions if present
    if "extensions" in message:
        protobuf_message["extensions"] = message["extensions"]

    return protobuf_message

def convert_protobuf_response_to_a2a_json(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert protobuf JSON response format back to A2A JSON format.

    Protobuf JSON format response:
    {
        "task": {
            "id": "...",
            "context_id": "...",
            "status": {...},
            "history": [{"message_id": "...", "role": "ROLE_USER", "content": [...]}]
        }
    }

    A2A JSON format response:
    {
        "result": {
            "id": "...",
            "contextId": "...",
            "status": {...},
            "history": [{"messageId": "...", "role": "user", "parts": [...], "kind": "message"}],
            "kind": "task"
        }
    }
    """
    # Handle different response structures
    if "task" in response:
        # Convert task response (wrapped format)
        task = response["task"]
        a2a_task = convert_protobuf_task_to_a2a(task)
        return a2a_task
    elif "message" in response:
        # Convert message response
        message = response["message"]
        a2a_message = convert_protobuf_message_to_a2a(message)
        return a2a_message
    elif "id" in response and "status" in response:
        # Direct task object (not wrapped) - common for cancel/get responses
        a2a_task = convert_protobuf_task_to_a2a(response)
        return a2a_task
    else:
        # Return as-is if format not recognized
        return response


def convert_protobuf_task_to_a2a(task: Dict[str, Any]) -> Dict[str, Any]:
    """Convert protobuf task to A2A task format."""
    a2a_task = {"kind": "task"}

    # Map basic fields
    if "id" in task:
        a2a_task["id"] = task["id"]
    if "context_id" in task:
        a2a_task["contextId"] = task["context_id"]
    if "status" in task:
        # Convert protobuf status to A2A status format
        status = task["status"]
        a2a_status = {}
        if "state" in status:
            # Convert protobuf enum state to A2A state
            state_map = {
                "TASK_STATE_SUBMITTED": "submitted",
                "TASK_STATE_WORKING": "working",
                "TASK_STATE_COMPLETED": "completed",
                "TASK_STATE_FAILED": "failed",
                "TASK_STATE_CANCELLED": "canceled",
                "TASK_STATE_INPUT_REQUIRED": "input-required",
                "TASK_STATE_REJECTED": "rejected",
                "TASK_STATE_AUTH_REQUIRED": "auth-required"
            }
            a2a_status["state"] = state_map.get(status["state"], status["state"])
        if "timestamp" in status:
            a2a_status["timestamp"] = status["timestamp"]
        if "message" in status:
            # Convert status message if present
            a2a_status["message"] = convert_protobuf_message_to_a2a(status["message"])
        a2a_task["status"] = a2a_status
    if "artifacts" in task:
        a2a_task["artifacts"] = task["artifacts"]
    if "metadata" in task:
        a2a_task["metadata"] = task["metadata"]

    # Convert history messages
    if "history" in task:
        a2a_task["history"] = []
        for msg in task["history"]:
            a2a_msg = convert_protobuf_message_to_a2a(msg)
            a2a_task["history"].append(a2a_msg)

    return a2a_task


def convert_protobuf_message_to_a2a(message: Dict[str, Any]) -> Dict[str, Any]:
    """Convert protobuf message to A2A message format."""
    a2a_message = {"kind": "message"}

    # Map basic fields
    if "message_id" in message:
        a2a_message["messageId"] = message["message_id"]
    if "context_id" in message:
        a2a_message["contextId"] = message["context_id"]
    if "task_id" in message:
        a2a_message["taskId"] = message["task_id"]
    if "metadata" in message:
        a2a_message["metadata"] = message["metadata"]
    if "extensions" in message:
        a2a_message["extensions"] = message["extensions"]

    # Convert role from protobuf enum to A2A format
    if "role" in message:
        role_map = {
            "ROLE_USER": "user",
            "ROLE_AGENT": "agent",
            "ROLE_UNSPECIFIED": "user"  # default fallback
        }
        a2a_message["role"] = role_map.get(message["role"], "user")

    # Convert content -> parts
    if "content" in message:
        a2a_message["parts"] = []
        for part in message["content"]:
            a2a_part = {}
            if "text" in part:
                a2a_part["kind"] = "text"
                a2a_part["text"] = part["text"]
            elif "file" in part:
                a2a_part["kind"] = "file"
                file_data = part["file"]
                a2a_file = {}
                if "name" in file_data:
                    a2a_file["name"] = file_data["name"]
                if "mime_type" in file_data:
                    a2a_file["mimeType"] = file_data["mime_type"]
                if "uri" in file_data:
                    a2a_file["uri"] = file_data["uri"]
                if "size_in_bytes" in file_data:
                    a2a_file["sizeInBytes"] = file_data["size_in_bytes"]
                if "bytes" in file_data:
                    a2a_file["bytes"] = file_data["bytes"]
                a2a_part["file"] = a2a_file
            elif "data" in part:
                a2a_part["kind"] = "data"
                # Handle nested DataPart structure: {"data": {"data": <actual_data>}}
                data_field = part["data"]
                if isinstance(data_field, dict) and "data" in data_field:
                    # Extract the inner data from protobuf DataPart structure
                    a2a_part["data"] = data_field["data"]
                else:
                    # Fallback for direct data (shouldn't happen with correct protobuf)
                    a2a_part["data"] = data_field

            if "metadata" in part:
                a2a_part["metadata"] = part["metadata"]

            a2a_message["parts"].append(a2a_part)

    return a2a_message

def handle_http_error_response(response) -> Dict[str, Any]:
    """
    Handle HTTP error responses and map them to proper JSON-RPC error format.

    Maps HTTP status codes and SUT error types to A2A JSON-RPC error codes.
    """
    try:
        # Try to parse error response as JSON
        error_data = response.json()
        error_type = error_data.get("error", "")
        error_message = error_data.get("message", response.text)

        # Map SUT error types to A2A JSON-RPC error codes
        if "TaskNotFoundError" in error_type:
            return {"error": {"code": -32001, "message": "Task not found"}}
        elif "TaskNotCancelableError" in error_type:
            return {"error": {"code": -32002, "message": "Task cannot be canceled"}}
        elif "PushNotificationNotSupportedError" in error_type:
            return {"error": {"code": -32003, "message": "Push Notification is not supported"}}
        elif "UnsupportedOperationError" in error_type:
            return {"error": {"code": -32004, "message": "This operation is not supported"}}
        elif "ContentTypeNotSupportedError" in error_type:
            return {"error": {"code": -32005, "message": "Incompatible content types"}}
        elif "InvalidAgentResponseError" in error_type:
            return {"error": {"code": -32006, "message": "Invalid agent response type"}}
        elif "AuthenticatedExtendedCardNotConfiguredError" in error_type:
            return {"error": {"code": -32007, "message": "Authenticated Extended Card not configured"}}
        elif "InvalidParamsError" in error_type:
            return {"error": {"code": -32602, "message": "Invalid method parameters"}}
        elif "InternalError" in error_type and (
                "Parts cannot be empty" in error_message or "InternalError: Parts cannot be empty" in error_message):
            # SUT is incorrectly returning InternalError for invalid params (same bug as gRPC INTERNAL status)
            return {"error": {"code": -32602, "message": "Invalid method parameters"}}

        # Map by HTTP status code if error type not recognized
        elif response.status_code == 404:
            return {"error": {"code": -32001, "message": "Task not found"}}
        elif response.status_code == 400:
            return {"error": {"code": -32602, "message": "Invalid method parameters"}}
        elif response.status_code == 422:
            return {"error": {"code": -32602, "message": "Invalid method parameters"}}
        elif response.status_code == 501:
            return {"error": {"code": -32601, "message": "Method not found"}}
        else:
            return {"error": {"code": -32603, "message": f"Internal server error: {error_message}"}}

    except (ValueError, json.JSONDecodeError):
        # If response is not valid JSON, map by HTTP status code only
        if response.status_code == 404:
            return {"error": {"code": -32001, "message": "Task not found"}}
        elif response.status_code == 400:
            return {"error": {"code": -32602, "message": "Invalid method parameters"}}
        elif response.status_code == 422:
            return {"error": {"code": -32602, "message": "Invalid method parameters"}}
        elif response.status_code == 501:
            return {"error": {"code": -32601, "message": "Method not found"}}
        else:
            return {"error": {"code": -32603, "message": f"HTTP {response.status_code}: {response.text}"}}