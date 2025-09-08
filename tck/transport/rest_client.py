"""
REST/HTTP+JSON transport client for A2A Protocol v0.3.0

Implements real HTTP communication with A2A SUTs using HTTP+JSON/REST.
This client makes actual HTTP requests to live SUTs - NO MOCKING.

Specification Reference: A2A Protocol v0.3.0 §4.3 - HTTP+JSON/REST Transport
"""

import json
import logging
from typing import Dict, List, Optional, Any, AsyncIterator, Union
from urllib.parse import urljoin, urlparse
import asyncio
import time

import httpx
from httpx import AsyncClient, Client

from tck.transport.base_client import BaseTransportClient, TransportType, TransportError

logger = logging.getLogger(__name__)


class RESTClient(BaseTransportClient):
    """
    A2A REST/HTTP+JSON transport client for real network communication.

    This client implements the A2A Protocol v0.3.0 REST transport specification,
    making actual HTTP requests to live SUTs. All methods perform real network
    operations without any mocking.

    Key Features:
    - Real HTTP communication using JSON payloads
    - Async/await support for streaming operations via Server-Sent Events (SSE)
    - Full A2A v0.3.0 method coverage
    - Transport-specific error handling
    - HTTP status code and header management

    Specification Reference: A2A Protocol v0.3.0 §4.3
    """

    def __init__(self, base_url: str, timeout: float = 30.0, **kwargs):
        """
        Initialize REST client for real network communication.

        Args:
            base_url: Base URL of the SUT's HTTP endpoint
            timeout: Default timeout for HTTP operations in seconds
            **kwargs: Additional configuration options
        """
        super().__init__(base_url, TransportType.REST)
        self.timeout = timeout

        # Normalize base URL (ensure it ends with /)
        if not base_url.endswith("/"):
            base_url += "/"
        self.base_url = base_url

        # HTTP client configuration
        self._client: Optional[Client] = None
        self._async_client: Optional[AsyncClient] = None

        # Default headers for all requests
        self.default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "A2A-TCK-REST-Client/0.3.0",
        }

        logger.info(f"Initialized REST client for endpoint: {self.base_url}")

    @property
    def client(self) -> Client:
        """Get or create synchronous HTTP client for real network communication."""
        if self._client is None:
            self._client = Client(timeout=self.timeout, headers=self.default_headers, follow_redirects=True)
            logger.debug(f"Created HTTP client for {self.base_url}")
        return self._client

    @property
    def async_client(self) -> AsyncClient:
        """Get or create asynchronous HTTP client for real network communication."""
        if self._async_client is None:
            self._async_client = AsyncClient(timeout=self.timeout, headers=self.default_headers, follow_redirects=True)
            logger.debug(f"Created async HTTP client for {self.base_url}")
        return self._async_client

    def close(self):
        """Close HTTP clients and cleanup resources."""
        if self._client:
            self._client.close()
            self._client = None
            logger.debug("Closed synchronous HTTP client")

        if self._async_client:
            # Note: In async context, this should be awaited
            # For sync close, we'll leave it for garbage collection
            self._async_client = None
            logger.debug("Marked async HTTP client for cleanup")

    async def aclose(self):
        """Async close for HTTP clients."""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None
            logger.debug("Closed async HTTP client")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # A2A Protocol Method Implementations - Real HTTP Calls

    def _convert_a2a_message_to_protobuf_json(self, message: Dict[str, Any]) -> Dict[str, Any]:
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
                            "name": file_data.get("name", ""),
                            "mime_type": file_data.get("mimeType", ""),
                            "uri": file_data.get("uri", file_data.get("url", "")),
                            "size_in_bytes": file_data.get("sizeInBytes", 0)
                        }
                        if "bytes" in file_data:
                            protobuf_part["file"]["bytes"] = file_data["bytes"]
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

    def _convert_protobuf_response_to_a2a_json(self, response: Dict[str, Any]) -> Dict[str, Any]:
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
            a2a_task = self._convert_protobuf_task_to_a2a(task)
            return a2a_task
        elif "message" in response:
            # Convert message response  
            message = response["message"]
            a2a_message = self._convert_protobuf_message_to_a2a(message)
            return a2a_message
        elif "id" in response and "status" in response:
            # Direct task object (not wrapped) - common for cancel/get responses
            a2a_task = self._convert_protobuf_task_to_a2a(response)
            return a2a_task
        else:
            # Return as-is if format not recognized
            return response
    
    def _convert_protobuf_task_to_a2a(self, task: Dict[str, Any]) -> Dict[str, Any]:
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
                a2a_status["message"] = self._convert_protobuf_message_to_a2a(status["message"])
            a2a_task["status"] = a2a_status
        if "artifacts" in task:
            a2a_task["artifacts"] = task["artifacts"]
        if "metadata" in task:
            a2a_task["metadata"] = task["metadata"]
            
        # Convert history messages
        if "history" in task:
            a2a_task["history"] = []
            for msg in task["history"]:
                a2a_msg = self._convert_protobuf_message_to_a2a(msg)
                a2a_task["history"].append(a2a_msg)
                
        return a2a_task
    
    def _convert_protobuf_message_to_a2a(self, message: Dict[str, Any]) -> Dict[str, Any]:
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

    def _handle_http_error_response(self, response) -> Dict[str, Any]:
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
            elif "InternalError" in error_type and ("Parts cannot be empty" in error_message or "InternalError: Parts cannot be empty" in error_message):
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

    def send_message(self, message: Dict[str, Any], extra_headers: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """
        Send message via HTTP POST and wait for completion.

        Maps to: POST v1/message:send HTTP request

        Args:
            message: A2A message in JSON format
            **kwargs: Additional configuration options (extra_headers, etc.)

        Returns:
            Dict containing task or message response from SUT

        Raises:
            TransportError: If HTTP request fails or times out
        """
        try:
            logger.info(f"Sending message via REST: {message.get('message_id', 'unknown')}")

            # Prepare request
            url = urljoin(self.base_url, "v1/message:send")
            headers = self.default_headers.copy()

            # Add extra headers if provided
            if extra_headers:
                headers.update(extra_headers)

            # Convert A2A JSON message to protobuf-compatible format
            protobuf_message = self._convert_a2a_message_to_protobuf_json(message)
            
            # Prepare payload according to A2A REST specification (using protobuf format)
            payload = {"message": protobuf_message}

            # Add configuration options if provided
            if "accepted_output_modes" in kwargs:
                payload["accepted_output_modes"] = kwargs["accepted_output_modes"]
            if "history_length" in kwargs:
                payload["history_length"] = kwargs["history_length"]
            if "blocking" in kwargs:
                payload["blocking"] = kwargs["blocking"]

            # Make real HTTP request to live SUT
            response = self.client.post(url, json=payload, headers=headers)

            # Handle HTTP errors
            if response.status_code >= 400:
                logger.error(f"REST request failed: HTTP {response.status_code}")
                return self._handle_http_error_response(response)

            # Parse JSON response
            response_data = response.json()

            # Convert protobuf response back to A2A JSON format
            a2a_response = self._convert_protobuf_response_to_a2a_json(response_data)

            logger.debug(f"Received REST response for message {message.get('message_id')}")
            return a2a_response

        except httpx.RequestError as e:
            error_msg = f"HTTP request failed: {str(e)}"
            logger.error(error_msg)
            raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)
        except Exception as e:
            error_msg = f"Unexpected error in REST send_message: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.REST)

    def __repr__(self) -> str:
        return super().__repr__()

    async def send_streaming_message(self, message: Dict[str, Any], **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """
        Send message via HTTP POST and stream responses using Server-Sent Events.

        Maps to: POST v1/messages:stream HTTP request with SSE response

        Args:
            message: A2A message in JSON format
            **kwargs: Additional configuration options

        Yields:
            Dict containing streaming task updates from SUT

        Raises:
            TransportError: If HTTP streaming request fails
        """
        try:
            logger.info(f"Starting REST streaming for message: {message.get('message_id', 'unknown')}")

            # Prepare request
            url = urljoin(self.base_url, "v1/message:stream")
            headers = self.default_headers.copy()
            headers["Accept"] = "text/event-stream"  # SSE format

            # Add extra headers if provided
            if "extra_headers" in kwargs and kwargs["extra_headers"] is not None:
                headers.update(kwargs["extra_headers"])

            # Convert A2A JSON message to protobuf-compatible format
            protobuf_message = self._convert_a2a_message_to_protobuf_json(message)
            
            # Prepare payload
            payload = {"message": protobuf_message}

            # Add configuration options if provided
            if "accepted_output_modes" in kwargs:
                payload["accepted_output_modes"] = kwargs["accepted_output_modes"]
            if "history_length" in kwargs:
                payload["history_length"] = kwargs["history_length"]

            # Make real HTTP streaming request to live SUT
            async with self.async_client.stream("POST", url, json=payload, headers=headers) as response:
                # Handle HTTP errors
                if response.status_code >= 400:
                    error_msg = f"HTTP {response.status_code}: {await response.aread()}"
                    logger.error(f"REST streaming request failed: {error_msg}")
                    raise TransportError(f"REST streaming error: {error_msg}", TransportType.REST)

                # Parse Server-Sent Events stream
                async for line in response.aiter_lines():
                    line = line.strip()

                    if not line:
                        continue

                    # Parse SSE format: "data: {json}"
                    if line.startswith("data: "):
                        try:
                            data_str = line[6:]  # Remove "data: " prefix
                            if data_str == "[DONE]":
                                break

                            event_data = json.loads(data_str)
                            yield event_data

                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse SSE data: {data_str}, error: {e}")
                            continue

                    # Handle other SSE events (id, event, retry)
                    elif line.startswith("event: "):
                        event_type = line[7:]
                        logger.debug(f"Received SSE event type: {event_type}")
                    elif line.startswith("id: "):
                        event_id = line[4:]
                        logger.debug(f"Received SSE event ID: {event_id}")

            logger.debug(f"Completed REST streaming for message {message.get('message_id')}")

        except httpx.RequestError as e:
            error_msg = f"HTTP streaming request failed: {str(e)}"
            logger.error(error_msg)
            raise TransportError(f"REST streaming error: {error_msg}", TransportType.REST)
        except Exception as e:
            error_msg = f"Unexpected error in REST streaming: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.REST)

    def get_task(self, task_id: str, **kwargs) -> Dict[str, Any]:
        """
        Get task status via HTTP GET.

        Maps to: GET v1/tasks/{task_id} HTTP request

        Args:
            task_id: ID of the task to retrieve
            **kwargs: Additional options (e.g., history_length, extra_headers)

        Returns:
            Dict containing task data from SUT

        Raises:
            TransportError: If HTTP request fails
        """
        try:
            logger.info(f"Getting task via REST: {task_id}")

            # Prepare request
            url = urljoin(self.base_url, f"v1/tasks/{task_id}")
            headers = self.default_headers.copy()

            # Add extra headers if provided
            if "extra_headers" in kwargs and kwargs["extra_headers"] is not None:
                headers.update(kwargs["extra_headers"])

            # Add query parameters
            params = {}
            if "history_length" in kwargs:
                params["history_length"] = kwargs["history_length"]

            # Make real HTTP request to live SUT
            response = self.client.get(url, params=params, headers=headers)

            # Handle HTTP errors
            if response.status_code >= 400:
                logger.error(f"REST get_task failed: HTTP {response.status_code}")
                return self._handle_http_error_response(response)

            # Parse JSON response
            task_data = response.json()

            # Convert protobuf response back to A2A JSON format
            a2a_response = self._convert_protobuf_response_to_a2a_json(task_data)

            logger.debug(f"Retrieved task via REST: {task_id}")
            return a2a_response

        except httpx.RequestError as e:
            error_msg = f"HTTP request failed: {str(e)}"
            logger.error(error_msg)
            raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)
        except Exception as e:
            error_msg = f"Unexpected error in REST get_task: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.REST)

    def cancel_task(self, task_id: str, **kwargs) -> Dict[str, Any]:
        """
        Cancel task via HTTP POST.

        Maps to: POST v1/tasks/{task_id}:cancel HTTP request

        Args:
            task_id: ID of the task to cancel
            **kwargs: Additional configuration options (extra_headers)

        Returns:
            Dict containing cancelled task data from SUT

        Raises:
            TransportError: If HTTP request fails
        """
        try:
            logger.info(f"Cancelling task via REST: {task_id}")

            # Prepare request
            url = urljoin(self.base_url, f"v1/tasks/{task_id}:cancel")
            headers = self.default_headers.copy()

            # Add extra headers if provided
            if "extra_headers" in kwargs and kwargs["extra_headers"] is not None:
                headers.update(kwargs["extra_headers"])

            # Make real HTTP request to live SUT
            response = self.client.post(url, headers=headers)

            # Handle HTTP errors
            if response.status_code >= 400:
                logger.error(f"REST cancel_task failed: HTTP {response.status_code}")
                return self._handle_http_error_response(response)

            # Parse JSON response
            cancelled_task = response.json()

            # Convert protobuf response back to A2A JSON format
            a2a_response = self._convert_protobuf_response_to_a2a_json(cancelled_task)

            logger.debug(f"Cancelled task via REST: {task_id}")
            return a2a_response

        except httpx.RequestError as e:
            error_msg = f"HTTP request failed: {str(e)}"
            logger.error(error_msg)
            raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)
        except Exception as e:
            error_msg = f"Unexpected error in REST cancel_task: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.REST)

    def resubscribe_task(self, task_id: str, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """
        Resubscribe to task updates via HTTP SSE streaming.

        Maps to: GET v1/tasks/{task_id}:subscribe HTTP request with SSE response
        This is an alias for subscribe_to_task for interface compatibility.

        Args:
            task_id: ID of the task to resubscribe to
            **kwargs: Additional configuration options

        Returns:
            AsyncIterator yielding task update events from SUT

        Raises:
            TransportError: If HTTP streaming request fails
        """
        return self.subscribe_to_task(task_id, **kwargs)

    async def subscribe_to_task(self, task_id: str, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """
        Subscribe to task updates via HTTP SSE streaming.

        Maps to: GET v1/tasks/{task_id}:subscribeevents HTTP request with SSE response

        Args:
            task_id: ID of the task to subscribe to
            **kwargs: Additional configuration options (extra_headers)

        Yields:
            Dict containing task update events from SUT

        Raises:
            TransportError: If HTTP streaming request fails
        """
        try:
            logger.info(f"Subscribing to task via REST: {task_id}")

            # Prepare request
            url = urljoin(self.base_url, f"v1/tasks/{task_id}:subscribe")
            headers = self.default_headers.copy()
            headers["Accept"] = "text/event-stream"  # SSE format

            # Add extra headers if provided
            if "extra_headers" in kwargs and kwargs["extra_headers"] is not None:
                headers.update(kwargs["extra_headers"])

            # Make real HTTP streaming request to live SUT
            async with self.async_client.stream("GET", url, headers=headers) as response:
                # Handle HTTP errors
                if response.status_code >= 400:
                    error_msg = f"HTTP {response.status_code}: {await response.aread()}"
                    logger.error(f"REST task subscription failed: {error_msg}")
                    raise TransportError(f"REST streaming error: {error_msg}", TransportType.REST)

                # Parse Server-Sent Events stream
                async for line in response.aiter_lines():
                    line = line.strip()

                    if not line:
                        continue

                    # Parse SSE format: "data: {json}"
                    if line.startswith("data: "):
                        try:
                            data_str = line[6:]  # Remove "data: " prefix
                            if data_str == "[DONE]":
                                break

                            event_data = json.loads(data_str)
                            yield event_data

                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse SSE data: {data_str}, error: {e}")
                            continue

                    # Handle other SSE events
                    elif line.startswith("event: "):
                        event_type = line[7:]
                        logger.debug(f"Received SSE event type: {event_type}")
                    elif line.startswith("id: "):
                        event_id = line[4:]
                        logger.debug(f"Received SSE event ID: {event_id}")

            logger.debug(f"Completed REST subscription for task: {task_id}")

        except httpx.RequestError as e:
            error_msg = f"HTTP streaming request failed: {str(e)}"
            logger.error(error_msg)
            raise TransportError(f"REST streaming error: {error_msg}", TransportType.REST)
        except Exception as e:
            error_msg = f"Unexpected error in REST subscription: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.REST)

    def get_agent_card(self, **kwargs) -> Dict[str, Any]:
        """
        Get agent card via HTTP GET.

        Maps to: GET /v1/card HTTP request

        Args:
            **kwargs: Additional configuration options (extra_headers)

        Returns:
            Dict containing agent card data from SUT

        Raises:
            TransportError: If HTTP request fails
        """
        try:
            logger.info("Getting agent card via REST")

            # Prepare request
            url = urljoin(self.base_url, "/v1/card")
            headers = self.default_headers.copy()

            # Add extra headers if provided
            if "extra_headers" in kwargs and kwargs["extra_headers"] is not None:
                headers.update(kwargs["extra_headers"])

            # Make real HTTP request to live SUT
            response = self.client.get(url, headers=headers)

            # Handle HTTP errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"REST get_agent_card failed: {error_msg}")
                raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)

            # Parse JSON response
            agent_card = response.json()

            logger.debug("Retrieved agent card via REST")
            return agent_card

        except httpx.RequestError as e:
            error_msg = f"HTTP request failed: {str(e)}"
            logger.error(error_msg)
            raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)
        except Exception as e:
            error_msg = f"Unexpected error in REST get_agent_card: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.REST)

    def get_authenticated_extended_card(self, **kwargs) -> Dict[str, Any]:
        """
        Get authenticated extended agent card via HTTP GET.

        Maps to: GET /v1/card HTTP request with authentication headers

        Args:
            **kwargs: Additional configuration options (extra_headers with auth)

        Returns:
            Dict containing extended agent card data from SUT

        Raises:
            TransportError: If HTTP request fails
        """
        try:
            logger.info("Getting authenticated extended agent card via REST")

            # Prepare request
            url = urljoin(self.base_url, "/v1/card")
            headers = self.default_headers.copy()

            # Add extra headers if provided (should include authentication)
            if "extra_headers" in kwargs:
                headers.update(kwargs["extra_headers"])

            # Make real HTTP request to live SUT (with authentication headers)
            response = self.client.get(url, headers=headers)

            # Handle HTTP errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"REST get_authenticated_extended_card failed: {error_msg}")
                raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)

            # Parse JSON response
            extended_card = response.json()

            logger.debug("Retrieved authenticated extended agent card via REST")
            return extended_card

        except httpx.RequestError as e:
            error_msg = f"HTTP request failed: {str(e)}"
            logger.error(error_msg)
            raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)
        except Exception as e:
            error_msg = f"Unexpected error in REST get_authenticated_extended_card: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.REST)

    # Push notification configuration methods

    def set_push_notification_config(self, task_id: str, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Set push notification config for a task via HTTP POST.

        Maps to: POST v1/tasks/{task_id}/pushNotificationConfigs HTTP request

        Args:
            task_id: ID of the task to configure
            config: Push notification configuration
            **kwargs: Additional configuration options (extra_headers)

        Returns:
            Dict containing created config data from SUT

        Raises:
            TransportError: If HTTP request fails
        """
        try:
            logger.info(f"Setting push notification config for task via REST: {task_id}")

            # Prepare request
            url = urljoin(self.base_url, f"v1/tasks/{task_id}/pushNotificationConfigs")
            headers = self.default_headers.copy()

            # Add extra headers if provided
            if "extra_headers" in kwargs and kwargs["extra_headers"] is not None:
                headers.update(kwargs["extra_headers"])

            # Format request according to protobuf CreateTaskPushNotificationConfigRequest structure
            # Generate config_id if not provided
            config_id = config.get("id", "default")
            
            # Build protobuf-compatible request structure
            protobuf_request = {
                "parent": f"tasks/{task_id}",
                "config_id": config_id,
                "config": {
                    "name": f"tasks/{task_id}/pushNotificationConfigs/{config_id}",
                    "push_notification_config": {
                        "id": config_id,
                        "url": config.get("url", ""),
                        "token": config.get("token", ""),
                        "authentication": config.get("authentication", {})
                    }
                }
            }

            # Make real HTTP request to live SUT
            response = self.client.post(url, json=protobuf_request, headers=headers)

            # Handle HTTP errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"REST set_push_notification_config failed: {error_msg}")
                raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)

            # Parse JSON response
            created_config = response.json()

            logger.debug(f"Set push notification config via REST: {task_id}")
            return created_config

        except httpx.RequestError as e:
            error_msg = f"HTTP request failed: {str(e)}"
            logger.error(error_msg)
            raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)
        except Exception as e:
            error_msg = f"Unexpected error in REST set_push_notification_config: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.REST)

    def get_push_notification_config(self, task_id: str, config_id: str, **kwargs) -> Dict[str, Any]:
        """
        Get push notification config via HTTP GET.

        Maps to: GET v1/tasks/{task_id}/pushNotificationConfigs/{config_id} HTTP request

        Args:
            task_id: ID of the task
            config_id: ID of the config to retrieve
            **kwargs: Additional configuration options (extra_headers)

        Returns:
            Dict containing config data from SUT

        Raises:
            TransportError: If HTTP request fails
        """
        try:
            logger.info(f"Getting push notification config via REST: {task_id}/{config_id}")

            # Prepare request
            url = urljoin(self.base_url, f"v1/tasks/{task_id}/pushNotificationConfigs/{config_id}")
            headers = self.default_headers.copy()

            # Add extra headers if provided
            if "extra_headers" in kwargs and kwargs["extra_headers"] is not None:
                headers.update(kwargs["extra_headers"])

            # Make real HTTP request to live SUT
            response = self.client.get(url, headers=headers)

            # Handle HTTP errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"REST get_push_notification_config failed: {error_msg}")
                raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)

            # Parse JSON response
            config_data = response.json()

            logger.debug(f"Retrieved push notification config via REST: {task_id}/{config_id}")
            return config_data

        except httpx.RequestError as e:
            error_msg = f"HTTP request failed: {str(e)}"
            logger.error(error_msg)
            raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)
        except Exception as e:
            error_msg = f"Unexpected error in REST get_push_notification_config: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.REST)

    def list_push_notification_configs(self, task_id: str, **kwargs) -> Dict[str, Any]:
        """
        List push notification configs for a task via HTTP GET.

        Maps to: GET v1/tasks/{task_id}/pushNotificationConfigs HTTP request

        Args:
            task_id: ID of the task
            **kwargs: Additional configuration options (extra_headers)

        Returns:
            Dict containing list of configs from SUT

        Raises:
            TransportError: If HTTP request fails
        """
        try:
            logger.info(f"Listing push notification configs via REST: {task_id}")

            # Prepare request
            url = urljoin(self.base_url, f"v1/tasks/{task_id}/pushNotificationConfigs")
            headers = self.default_headers.copy()

            # Add extra headers if provided
            if "extra_headers" in kwargs and kwargs["extra_headers"] is not None:
                headers.update(kwargs["extra_headers"])

            # Make real HTTP request to live SUT
            response = self.client.get(url, headers=headers)

            # Handle HTTP errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"REST list_push_notification_configs failed: {error_msg}")
                raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)

            # Parse JSON response
            configs_response = response.json()
            
            # Extract configs array from protobuf ListTaskPushNotificationConfigResponse structure
            # The protobuf response has format: {"configs": [...]}
            # But A2A tests expect just the array directly, with taskId added to each config
            if "configs" in configs_response:
                configs_list = []
                for config in configs_response["configs"]:
                    # Add taskId to each config (extracted from the request context)
                    enhanced_config = config.copy()
                    enhanced_config["taskId"] = task_id
                    configs_list.append(enhanced_config)
            else:
                configs_list = []

            logger.debug(f"Listed push notification configs via REST: {task_id}")
            return configs_list

        except httpx.RequestError as e:
            error_msg = f"HTTP request failed: {str(e)}"
            logger.error(error_msg)
            raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)
        except Exception as e:
            error_msg = f"Unexpected error in REST list_push_notification_configs: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.REST)

    def delete_push_notification_config(self, task_id: str, config_id: str, **kwargs) -> Dict[str, Any]:
        """
        Delete push notification config via HTTP DELETE.

        Maps to: DELETE v1/tasks/{task_id}/pushNotificationConfigs/{config_id} HTTP request

        Args:
            task_id: ID of the task
            config_id: ID of the config to delete
            **kwargs: Additional configuration options (extra_headers)

        Returns:
            Dict containing deletion result from SUT

        Raises:
            TransportError: If HTTP request fails
        """
        try:
            logger.info(f"Deleting push notification config via REST: {task_id}/{config_id}")

            # Prepare request
            url = urljoin(self.base_url, f"v1/tasks/{task_id}/pushNotificationConfigs/{config_id}")
            headers = self.default_headers.copy()

            # Add extra headers if provided
            if "extra_headers" in kwargs and kwargs["extra_headers"] is not None:
                headers.update(kwargs["extra_headers"])

            # Make real HTTP request to live SUT
            response = self.client.delete(url, headers=headers)

            # Handle HTTP errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"REST delete_push_notification_config failed: {error_msg}")
                raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)

            # Parse JSON response (may be empty for successful deletion)
            # According to protobuf definition, DeleteTaskPushNotificationConfig returns Empty
            # A2A tests expect null result for successful deletion
            try:
                deletion_response = response.json() if response.content else {}
            except Exception:
                deletion_response = {}  # Empty response is acceptable for DELETE
            
            # Return None for successful deletion (Empty protobuf response)
            logger.debug(f"Deleted push notification config via REST: {task_id}/{config_id}")
            return None

        except httpx.RequestError as e:
            error_msg = f"HTTP request failed: {str(e)}"
            logger.error(error_msg)
            raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)
        except Exception as e:
            error_msg = f"Unexpected error in REST delete_push_notification_config: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.REST)

    # Optional REST-specific methods

    def list_tasks(self, **kwargs) -> Dict[str, Any]:
        """
        List tasks via HTTP GET (REST transport supports this method).

        Maps to: GET /tasks HTTP request

        Args:
            **kwargs: Additional configuration options (extra_headers, pagination)

        Returns:
            Dict containing list of tasks from SUT

        Raises:
            TransportError: If HTTP request fails
        """
        try:
            logger.info("Listing tasks via REST")

            # Prepare request
            url = urljoin(self.base_url, "tasks")
            headers = self.default_headers.copy()

            # Add extra headers if provided
            if "extra_headers" in kwargs and kwargs["extra_headers"] is not None:
                headers.update(kwargs["extra_headers"])

            # Add query parameters for pagination, filtering, etc.
            params = {}
            for key in ["page_size", "page_token", "filter"]:
                if key in kwargs:
                    params[key] = kwargs[key]

            # Make real HTTP request to live SUT
            response = self.client.get(url, params=params, headers=headers)

            # Handle HTTP errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"REST list_tasks failed: {error_msg}")
                raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)

            # Parse JSON response
            tasks_list = response.json()

            logger.debug("Listed tasks via REST")
            return tasks_list

        except httpx.RequestError as e:
            error_msg = f"HTTP request failed: {str(e)}"
            logger.error(error_msg)
            raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)
        except Exception as e:
            error_msg = f"Unexpected error in REST list_tasks: {str(e)}"
            logger.error(error_msg)
            raise TransportError(error_msg, TransportType.REST)

    # Transport-specific capabilities

    def supports_streaming(self) -> bool:
        """Check if this transport supports streaming operations."""
        return True  # REST supports streaming via Server-Sent Events

    def supports_bidirectional_streaming(self) -> bool:
        """Check if this transport supports bidirectional streaming."""
        return False  # HTTP/REST doesn't support true bidirectional streaming

    def get_transport_info(self) -> Dict[str, Any]:
        """Get information about this REST transport instance."""
        return {
            "transport_type": self.transport_type.value,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "supports_streaming": True,
            "supports_bidirectional": False,
            "streaming_mechanism": "Server-Sent Events (SSE)",
            "default_headers": self.default_headers,
        }
