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

    def send_message(self, message: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Send message via HTTP POST and wait for completion.

        Maps to: POST /messages HTTP request

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
            url = urljoin(self.base_url, "messages")
            headers = self.default_headers.copy()

            # Add extra headers if provided
            if "extra_headers" in kwargs:
                headers.update(kwargs["extra_headers"])

            # Prepare payload according to A2A REST specification
            payload = {"message": message}

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
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"REST request failed: {error_msg}")
                raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)

            # Parse JSON response
            response_data = response.json()

            logger.debug(f"Received REST response for message {message.get('message_id')}")
            return response_data

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

    async def send_streaming_message(self, message: Dict[str, Any], **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """
        Send message via HTTP POST and stream responses using Server-Sent Events.

        Maps to: POST /messages/stream HTTP request with SSE response

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
            url = urljoin(self.base_url, "messages/stream")
            headers = self.default_headers.copy()
            headers["Accept"] = "text/event-stream"  # SSE format

            # Add extra headers if provided
            if "extra_headers" in kwargs:
                headers.update(kwargs["extra_headers"])

            # Prepare payload
            payload = {"message": message}

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

        Maps to: GET /tasks/{task_id} HTTP request

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
            url = urljoin(self.base_url, f"tasks/{task_id}")
            headers = self.default_headers.copy()

            # Add extra headers if provided
            if "extra_headers" in kwargs:
                headers.update(kwargs["extra_headers"])

            # Add query parameters
            params = {}
            if "history_length" in kwargs:
                params["history_length"] = kwargs["history_length"]

            # Make real HTTP request to live SUT
            response = self.client.get(url, params=params, headers=headers)

            # Handle HTTP errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"REST get_task failed: {error_msg}")
                raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)

            # Parse JSON response
            task_data = response.json()

            logger.debug(f"Retrieved task via REST: {task_id}")
            return task_data

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

        Maps to: POST /tasks/{task_id}/cancel HTTP request

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
            url = urljoin(self.base_url, f"tasks/{task_id}/cancel")
            headers = self.default_headers.copy()

            # Add extra headers if provided
            if "extra_headers" in kwargs:
                headers.update(kwargs["extra_headers"])

            # Make real HTTP request to live SUT
            response = self.client.post(url, headers=headers)

            # Handle HTTP errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"REST cancel_task failed: {error_msg}")
                raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)

            # Parse JSON response
            cancelled_task = response.json()

            logger.debug(f"Cancelled task via REST: {task_id}")
            return cancelled_task

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

        Maps to: GET /tasks/{task_id}/events HTTP request with SSE response
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

        Maps to: GET /tasks/{task_id}/events HTTP request with SSE response

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
            url = urljoin(self.base_url, f"tasks/{task_id}/events")
            headers = self.default_headers.copy()
            headers["Accept"] = "text/event-stream"  # SSE format

            # Add extra headers if provided
            if "extra_headers" in kwargs:
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

        Maps to: GET /agent-card HTTP request

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
            url = urljoin(self.base_url, "agent-card")
            headers = self.default_headers.copy()

            # Add extra headers if provided
            if "extra_headers" in kwargs:
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

        Maps to: GET /agent-card HTTP request with authentication headers

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
            url = urljoin(self.base_url, "agent-card")
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

        Maps to: POST /tasks/{task_id}/push-notification-configs HTTP request

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
            url = urljoin(self.base_url, f"tasks/{task_id}/push-notification-configs")
            headers = self.default_headers.copy()

            # Add extra headers if provided
            if "extra_headers" in kwargs:
                headers.update(kwargs["extra_headers"])

            # Make real HTTP request to live SUT
            response = self.client.post(url, json=config, headers=headers)

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

        Maps to: GET /tasks/{task_id}/push-notification-configs/{config_id} HTTP request

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
            url = urljoin(self.base_url, f"tasks/{task_id}/push-notification-configs/{config_id}")
            headers = self.default_headers.copy()

            # Add extra headers if provided
            if "extra_headers" in kwargs:
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

        Maps to: GET /tasks/{task_id}/push-notification-configs HTTP request

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
            url = urljoin(self.base_url, f"tasks/{task_id}/push-notification-configs")
            headers = self.default_headers.copy()

            # Add extra headers if provided
            if "extra_headers" in kwargs:
                headers.update(kwargs["extra_headers"])

            # Make real HTTP request to live SUT
            response = self.client.get(url, headers=headers)

            # Handle HTTP errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"REST list_push_notification_configs failed: {error_msg}")
                raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)

            # Parse JSON response
            configs_list = response.json()

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

        Maps to: DELETE /tasks/{task_id}/push-notification-configs/{config_id} HTTP request

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
            url = urljoin(self.base_url, f"tasks/{task_id}/push-notification-configs/{config_id}")
            headers = self.default_headers.copy()

            # Add extra headers if provided
            if "extra_headers" in kwargs:
                headers.update(kwargs["extra_headers"])

            # Make real HTTP request to live SUT
            response = self.client.delete(url, headers=headers)

            # Handle HTTP errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"REST delete_push_notification_config failed: {error_msg}")
                raise TransportError(f"REST transport error: {error_msg}", TransportType.REST)

            # Parse JSON response (may be empty for successful deletion)
            try:
                deletion_result = response.json() if response.content else {}
            except Exception:
                deletion_result = {}  # Empty response is acceptable for DELETE

            logger.debug(f"Deleted push notification config via REST: {task_id}/{config_id}")
            return deletion_result

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
            if "extra_headers" in kwargs:
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
