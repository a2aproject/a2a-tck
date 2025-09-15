"""
JSON-RPC 2.0 Transport Client for A2A Protocol v0.3.0

This module implements the JSON-RPC 2.0 transport client for the A2A Test Compatibility Kit.
It provides real network communication with A2A SUTs over JSON-RPC 2.0 protocol,
making actual HTTP requests to validate protocol compliance.

This is an enhanced version of the original SUTClient that inherits from BaseTransportClient
while maintaining 100% backward compatibility with existing tests.

Specification Reference: A2A Protocol v0.3.0 §3.2.1 - JSON-RPC 2.0 Transport
"""

import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union, cast, Iterator, AsyncIterator

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tck.transport.base_client import BaseTransportClient, TransportType, TransportError

logger = logging.getLogger(__name__)


class JSONRPCError(TransportError):
    """
    JSON-RPC specific transport error.

    Represents errors that occur during JSON-RPC communication with the SUT.
    """

    def __init__(self, message: str, original_error: Optional[Exception] = None, json_rpc_error: Optional[Dict[str, Any]] = None):
        super().__init__(message, TransportType.JSON_RPC, json_rpc_error, original_error)
        self.json_rpc_error = json_rpc_error


class JSONRPCClient(BaseTransportClient):
    """
    JSON-RPC 2.0 transport client for A2A protocol compliance testing.

    This client makes real network calls to A2A SUTs over JSON-RPC 2.0 protocol
    to validate actual protocol compliance. It maintains backward compatibility
    with the existing SUTClient while implementing the BaseTransportClient interface.

    The client performs actual HTTP requests to live SUT endpoints, making it
    suitable for integration testing and compliance validation.

    Specification Reference: A2A Protocol v0.3.0 §3.2.1 - JSON-RPC 2.0 Transport
    """

    def __init__(self, base_url: str, timeout: float = 30.0, max_retries: int = 3):
        """
        Initialize the JSON-RPC client for real network communication.

        Args:
            base_url: Base URL of the A2A SUT's JSON-RPC endpoint
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts for failed requests
        """
        super().__init__(base_url, TransportType.JSON_RPC)

        self.timeout = timeout
        self.max_retries = max_retries
        
        # Configure streaming timeout from environment or use reasonable default
        base_timeout = float(os.getenv("TCK_STREAMING_TIMEOUT", "30.0"))
        self.streaming_timeout = base_timeout * 2  # Double the base timeout for streaming

        # Configure session with retry strategy for reliable network communication
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,
            allowed_methods=["HEAD", "GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self._logger.info(f"JSON-RPC client initialized for {base_url} (streaming timeout: {self.streaming_timeout}s)")

    def _generate_id(self) -> str:
        """Generate a unique request ID for JSON-RPC requests."""
        return f"tck-{uuid.uuid4()}"

    def _make_jsonrpc_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a JSON-RPC 2.0 request to the SUT.

        This method performs actual network communication with the SUT endpoint.

        Args:
            method: JSON-RPC method name
            params: Method parameters
            request_id: Request ID (auto-generated if not provided)
            extra_headers: Additional HTTP headers

        Returns:
            JSON-RPC response from the SUT

        Raises:
            JSONRPCError: If the request fails or returns an error
        """
        # Build JSON-RPC 2.0 request
        jsonrpc_request = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": request_id or self._generate_id()}

        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)

        self._logger.info(f"Sending JSON-RPC request to {self.base_url}: {jsonrpc_request}")

        try:
            # Make actual HTTP request to live SUT
            response = self.session.post(self.base_url, json=jsonrpc_request, headers=headers, timeout=self.timeout)

            self._logger.info(f"SUT responded with {response.status_code}: {response.text}")
            response.raise_for_status()

        except requests.RequestException as e:
            error_msg = f"HTTP error communicating with SUT at {self.base_url}: {e}"
            self._logger.error(error_msg)
            raise JSONRPCError(error_msg, original_error=e)

        # Parse JSON response
        try:
            json_response = response.json()
        except ValueError as e:
            error_msg = f"Failed to parse JSON response from SUT: {e}"
            self._logger.error(error_msg)
            raise JSONRPCError(error_msg, original_error=e)

        # Check for JSON-RPC error
        if "error" in json_response:
            error_msg = f"JSON-RPC error from SUT: {json_response['error']}"
            self._logger.error(error_msg)
            raise JSONRPCError(error_msg, json_rpc_error=json_response["error"])

        return json_response

    async def _make_streaming_jsonrpc_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Make a JSON-RPC 2.0 request that expects Server-Sent Events (SSE) response.

        This method performs actual network communication with the SUT endpoint
        and expects a streaming response with text/event-stream content type.

        Args:
            method: JSON-RPC method name
            params: Method parameters
            request_id: Request ID (auto-generated if not provided)
            extra_headers: Additional HTTP headers

        Yields:
            Individual JSON-RPC responses parsed from SSE events

        Raises:
            JSONRPCError: If the request fails or returns an error

        Specification Reference: A2A Protocol v0.3.0 §3.3 - Streaming Transport
        """
        # Build JSON-RPC 2.0 request
        jsonrpc_request = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": request_id or self._generate_id()}

        # Prepare headers
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        if extra_headers:
            headers.update(extra_headers)

        self._logger.info(f"Sending streaming JSON-RPC request to {self.base_url}: {jsonrpc_request}")

        try:
            # Use requests.Session for streaming with stream=True
            response = self.session.post(
                self.base_url, 
                json=jsonrpc_request, 
                headers=headers, 
                timeout=self.streaming_timeout,
                stream=True
            )
            
            self._logger.info(f"SUT responded with {response.status_code}, content-type: {response.headers.get('content-type')}")
            
            # Validate response status
            response.raise_for_status()
            
            # Validate content type for SSE
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("text/event-stream"):
                raise JSONRPCError(f"Expected text/event-stream content type for streaming, got: {content_type}")

            # Parse Server-Sent Events stream
            for line in response.iter_lines(decode_unicode=True):
                if line is None:
                    continue
                    
                line = line.strip()
                
                if not line:
                    continue
                    
                # Parse SSE format: "data: {json}"
                if line.startswith("data: "):
                    try:
                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str == "[DONE]":
                            break
                        self._logger.info(f"******** Received SSE data: {data_str}")
                        event_data = json.loads(data_str)
                        # Check for JSON-RPC error in the event
                        if "error" in event_data:
                            error_msg = f"JSON-RPC error from streaming SUT: {event_data['error']}"
                            self._logger.error(error_msg)
                            raise JSONRPCError(error_msg, json_rpc_error=event_data["error"])
                        
                        yield event_data
                        
                    except json.JSONDecodeError as e:
                        self._logger.warning(f"Failed to parse SSE data: {data_str}, error: {e}")
                        continue
                        
                # Handle other SSE events (id, event, retry)
                elif line.startswith("event: "):
                    event_type = line[7:]
                    self._logger.debug(f"Received SSE event type: {event_type}")
                elif line.startswith("id: "):
                    event_id = line[4:]
                    self._logger.debug(f"Received SSE event ID: {event_id}")

        except requests.RequestException as e:
            error_msg = f"HTTP error communicating with SUT at {self.base_url}: {e}"
            self._logger.error(error_msg)
            raise JSONRPCError(error_msg, original_error=e)
        except Exception as e:
            error_msg = f"Unexpected error in streaming request: {e}"
            self._logger.error(error_msg)
            raise JSONRPCError(error_msg, original_error=e)

    def send_message(self, message: Dict[str, Any], extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Send a message to the A2A server using the message/send method.

        Makes a real JSON-RPC call to validate the SUT's message handling capability.

        Args:
            message: The message object conforming to A2A Message schema
            extra_headers: Optional HTTP headers

        Returns:
            The response from the server containing task information

        Raises:
            JSONRPCError: If the message sending fails

        Specification Reference: A2A Protocol v0.3.0 §7.1 - Core Message Protocol
        """
        try:
            response = self._make_jsonrpc_request(method="message/send", params={"message": message}, extra_headers=extra_headers)
            return response.get("result", {})

        except Exception as e:
            if isinstance(e, JSONRPCError):
                raise
            raise JSONRPCError(f"Failed to send message: {e}", original_error=e)

    async def send_streaming_message(
        self, message: Dict[str, Any], extra_headers: Optional[Dict[str, str]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Send a message with streaming response using message/stream method.

        Makes a real JSON-RPC call with Server-Sent Events to test streaming functionality.
        This method yields the initial task creation and initial updates, but doesn't consume
        the entire stream to allow resubscribe_task to work properly.

        Args:
            message: The message object conforming to A2A Message schema
            extra_headers: Optional HTTP headers

        Returns:
            AsyncIterator that yields task updates from the real SUT SSE stream

        Raises:
            JSONRPCError: If streaming message sending fails

        Specification Reference: A2A Protocol v0.3.0 §3.3 - Streaming Transport
        """
        try:
            # Use the new streaming method that properly handles SSE
            event_count = 0
            async for event in self._make_streaming_jsonrpc_request(
                method="message/stream", params={"message": message}, extra_headers=extra_headers
            ):
                # Extract result from JSON-RPC response
                result = event.get("result")
                if result:
                    yield result
                    event_count += 1
                    
                    # Only yield the first few events to avoid consuming the entire stream
                    # This allows resubscribe_task to work properly later
                    if event_count >= 2:
                        break

        except Exception as e:
            if isinstance(e, JSONRPCError):
                raise
            raise JSONRPCError(f"Failed to send streaming message: {e}", original_error=e)

    def get_task(
        self, task_id: str, history_length: Optional[int] = None, extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Get task status and information using tasks/get method.

        Makes a real JSON-RPC call to retrieve task information from the SUT.

        Args:
            task_id: The unique identifier of the task
            history_length: Optional number of historical state transitions to include
            extra_headers: Optional HTTP headers

        Returns:
            The task object with current status and information

        Raises:
            JSONRPCError: If task retrieval fails

        Specification Reference: A2A Protocol v0.3.0 §7.3 - Task Retrieval
        """
        try:
            params = {"id": task_id}
            if history_length is not None:
                params["historyLength"] = history_length

            response = self._make_jsonrpc_request(method="tasks/get", params=params, extra_headers=extra_headers)
            return response.get("result", {})

        except Exception as e:
            if isinstance(e, JSONRPCError):
                raise
            raise JSONRPCError(f"Failed to get task {task_id}: {e}", original_error=e)

    def cancel_task(self, task_id: str, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Cancel a task using tasks/cancel method.

        Makes a real JSON-RPC call to cancel a task on the SUT.

        Args:
            task_id: The unique identifier of the task to cancel
            extra_headers: Optional HTTP headers

        Returns:
            The response confirming task cancellation

        Raises:
            JSONRPCError: If task cancellation fails

        Specification Reference: A2A Protocol v0.3.0 §7.4 - Task Cancellation
        """
        try:
            response = self._make_jsonrpc_request(method="tasks/cancel", params={"id": task_id}, extra_headers=extra_headers)
            return response.get("result", {})

        except Exception as e:
            if isinstance(e, JSONRPCError):
                raise
            raise JSONRPCError(f"Failed to cancel task {task_id}: {e}", original_error=e)

    async def resubscribe_task(self, task_id: str, extra_headers: Optional[Dict[str, str]] = None) -> AsyncIterator[Dict[str, Any]]:
        """
        Resubscribe to task updates using tasks/resubscribe method.

        Makes a real JSON-RPC call to resubscribe to task updates via SSE.

        Args:
            task_id: The unique identifier of the task to resubscribe to
            extra_headers: Optional HTTP headers

        Returns:
            AsyncIterator that yields task updates from the real SUT SSE stream

        Raises:
            JSONRPCError: If task resubscription fails

        Specification Reference: A2A Protocol v0.3.0 §7.9 - Task Resubscription
        """
        try:
            # Use the new streaming method that properly handles SSE
            async for event in self._make_streaming_jsonrpc_request(
                method="tasks/resubscribe", params={"id": task_id}, extra_headers=extra_headers
            ):
                # Extract result from JSON-RPC response
                result = event.get("result")
                if result:
                    yield result

        except Exception as e:
            if isinstance(e, JSONRPCError):
                raise
            raise JSONRPCError(f"Failed to resubscribe to task {task_id}: {e}", original_error=e)

    async def subscribe_to_task(self, task_id: str, extra_headers: Optional[Dict[str, str]] = None) -> AsyncIterator[Dict[str, Any]]:
        """
        Subscribe to task updates using tasks/subscribe method.

        This is an alias for resubscribe_task to maintain interface compatibility
        with other transport clients. JSON-RPC uses the same subscription mechanism
        for both initial subscription and resubscription.

        Args:
            task_id: The unique identifier of the task to subscribe to
            extra_headers: Optional HTTP headers

        Returns:
            AsyncIterator that yields task updates from the real SUT

        Raises:
            JSONRPCError: If task subscription fails

        Specification Reference: A2A Protocol v0.3.0 §7.9 - Task Subscription
        """
        # JSON-RPC uses the same method for both subscribe and resubscribe
        async for result in self.resubscribe_task(task_id, extra_headers):
            yield result

    def get_agent_card(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Get agent card using agent/getAuthenticatedExtendedCard method.

        Makes a real JSON-RPC call to get the agent card information.

        Args:
            extra_headers: Optional HTTP headers

        Returns:
            Dict containing agent card data from the real SUT

        Raises:
            JSONRPCError: If agent card retrieval fails

        Specification Reference: A2A Protocol v0.3.0 §5.5 - Agent Card Retrieval
        """
        try:
            response = self._make_jsonrpc_request(method="agent/getAuthenticatedExtendedCard", params={}, extra_headers=extra_headers)
            return response.get("result", {})

        except Exception as e:
            if isinstance(e, JSONRPCError):
                raise
            raise JSONRPCError(f"Failed to get agent card: {e}", original_error=e)

    def set_push_notification_config(
        self, task_id: str, config: Dict[str, Any], extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Set push notification configuration for a task.

        Makes a real JSON-RPC call to configure push notifications.

        Args:
            task_id: The unique identifier of the task
            config: Push notification configuration object
            extra_headers: Optional HTTP headers

        Returns:
            The response confirming configuration was set

        Raises:
            JSONRPCError: If configuration setting fails

        Specification Reference: A2A Protocol v0.3.0 §7.3 - Push Notifications
        """
        try:
            response = self._make_jsonrpc_request(
                method="tasks/pushNotificationConfig/set",
                params={"taskId": task_id, "pushNotificationConfig": config},
                extra_headers=extra_headers,
            )
            return response.get("result", {})

        except Exception as e:
            if isinstance(e, JSONRPCError):
                raise
            raise JSONRPCError(f"Failed to set push notification config for task {task_id}: {e}", original_error=e)

    def get_push_notification_config(
        self, task_id: str, config_id: str, extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Get push notification configuration for a task.

        Makes a real JSON-RPC call to retrieve push notification configuration.

        Args:
            task_id: The unique identifier of the task
            config_id: The unique identifier of the configuration
            extra_headers: Optional HTTP headers

        Returns:
            The push notification configuration object

        Raises:
            JSONRPCError: If configuration retrieval fails

        Specification Reference: A2A Protocol v0.3.0 §7.3.2 - Get Push Notification Config
        """
        try:
            response = self._make_jsonrpc_request(
                method="tasks/pushNotificationConfig/get",
                params={"id": task_id, "pushNotificationConfigId": config_id},
                extra_headers=extra_headers,
            )
            return response.get("result", {})

        except Exception as e:
            if isinstance(e, JSONRPCError):
                raise
            raise JSONRPCError(f"Failed to get push notification config {config_id} for task {task_id}: {e}", original_error=e)

    def list_push_notification_configs(self, task_id: str, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        List all push notification configurations for a task.

        Makes a real JSON-RPC call to list push notification configurations.

        Args:
            task_id: The unique identifier of the task
            extra_headers: Optional HTTP headers

        Returns:
            List of push notification configurations

        Raises:
            JSONRPCError: If configuration listing fails

        Specification Reference: A2A Protocol v0.3.0 §7.3.3 - List Push Notification Configs
        """
        try:
            response = self._make_jsonrpc_request(
                method="tasks/pushNotificationConfig/list", params={"id": task_id}, extra_headers=extra_headers
            )
            return response.get("result", {})

        except Exception as e:
            if isinstance(e, JSONRPCError):
                raise
            raise JSONRPCError(f"Failed to list push notification configs for task {task_id}: {e}", original_error=e)

    def delete_push_notification_config(
        self, task_id: str, config_id: str, extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Delete a push notification configuration for a task.

        Makes a real JSON-RPC call to delete push notification configuration.

        Args:
            task_id: The unique identifier of the task
            config_id: The unique identifier of the configuration to delete
            extra_headers: Optional HTTP headers

        Returns:
            The response confirming configuration was deleted

        Raises:
            JSONRPCError: If configuration deletion fails

        Specification Reference: A2A Protocol v0.3.0 §7.3.4 - Delete Push Notification Config
        """
        try:
            response = self._make_jsonrpc_request(
                method="tasks/pushNotificationConfig/delete",
                params={"id": task_id, "pushNotificationConfigId": config_id},
                extra_headers=extra_headers,
            )
            return response.get("result", {})

        except Exception as e:
            if isinstance(e, JSONRPCError):
                raise
            raise JSONRPCError(f"Failed to delete push notification config {config_id} for task {task_id}: {e}", original_error=e)

    def get_authenticated_extended_card(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Get the authenticated extended agent card.

        Makes a real JSON-RPC call to retrieve extended agent information.

        Args:
            extra_headers: Optional HTTP headers (typically auth headers)

        Returns:
            The extended agent card with additional authenticated information

        Raises:
            JSONRPCError: If authenticated card retrieval fails

        Specification Reference: A2A Protocol v0.3.0 §5.6 - Authenticated Extended Card
        """
        try:
            response = self._make_jsonrpc_request(
                method="agent/getAuthenticatedExtendedCard", params={}, extra_headers=extra_headers
            )
            return response.get("result", {})

        except Exception as e:
            if isinstance(e, JSONRPCError):
                raise
            raise JSONRPCError(f"Failed to get authenticated extended card: {e}", original_error=e)

    # Legacy methods for backward compatibility with existing SUTClient usage

    def raw_send(self, raw_data: str) -> Tuple[int, str]:
        """
        Send raw data to the SUT endpoint without JSON validation.

        This method maintains backward compatibility for protocol violation testing.

        Args:
            raw_data: The raw string data to send

        Returns:
            A tuple of (status_code, response_text)
        """
        headers = {"Content-Type": "application/json"}

        self._logger.info(f"Sending raw data to {self.base_url}: {raw_data}")

        try:
            response = self.session.post(self.base_url, data=raw_data, headers=headers, timeout=self.timeout)
            self._logger.info(f"SUT responded with {response.status_code}: {response.text}")
            return response.status_code, response.text
        except requests.exceptions.RequestException as e:
            self._logger.error(f"HTTP request failed: {e}")
            raise

    def send_raw_json_rpc(self, json_request: dict) -> Dict[str, Any]:
        """
        Send a JSON-RPC request without validation.

        This method maintains backward compatibility for malformed request testing.

        Args:
            json_request: The JSON-RPC request as a dictionary (can be malformed)

        Returns:
            The JSON response from the SUT
        """
        headers = {"Content-Type": "application/json"}

        self._logger.info(f"Sending raw JSON-RPC request to {self.base_url}: {json_request}")

        try:
            response = self.session.post(self.base_url, json=json_request, headers=headers, timeout=self.timeout)
            self._logger.info(f"SUT responded with {response.status_code}: {response.text}")
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())
        except requests.RequestException as e:
            self._logger.error(f"HTTP error communicating with SUT: {e}")
            raise
        except ValueError as e:
            self._logger.error(f"Failed to parse JSON response from SUT: {e}")
            raise

    def close(self):
        """Close the HTTP session."""
        if hasattr(self, "session"):
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
