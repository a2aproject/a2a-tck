"""
Unit tests for RESTClient - A2A v0.3.0 REST/HTTP+JSON transport implementation.

These tests verify the RESTClient follows the BaseTransportClient interface
and correctly handles HTTP-specific operations for real network communication.

Note: These are unit tests that mock HTTP calls. The actual TCK tests will
make real network calls to live SUTs without mocking.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
import json
from typing import Dict, Any

from tck.transport.rest_client import RESTClient
from tck.transport.base_client import TransportType, TransportError


@pytest.mark.core
class TestRESTClientInitialization:
    """Test RESTClient initialization and configuration."""

    def test_init_with_http_url(self):
        """Test initialization with HTTP URL."""
        client = RESTClient("http://example.com:8080")
        assert client.transport_type == TransportType.REST
        assert client.base_url == "http://example.com:8080/"
        assert client.timeout == 30.0

    def test_init_with_https_url(self):
        """Test initialization with HTTPS URL."""
        client = RESTClient("https://example.com:8080")
        assert client.transport_type == TransportType.REST
        assert client.base_url == "https://example.com:8080/"

    def test_init_with_trailing_slash(self):
        """Test initialization with URL that already has trailing slash."""
        client = RESTClient("https://example.com:8080/")
        assert client.base_url == "https://example.com:8080/"

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        client = RESTClient("https://example.com:8080", timeout=60.0)
        assert client.timeout == 60.0

    def test_default_headers(self):
        """Test default headers are set correctly."""
        client = RESTClient("https://example.com:8080")
        expected_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "A2A-TCK-REST-Client/0.3.0",
        }
        assert client.default_headers == expected_headers


@pytest.mark.core
class TestRESTClientInterface:
    """Test RESTClient implements BaseTransportClient interface correctly."""

    def test_implements_base_interface(self):
        """Test RESTClient implements all required methods."""
        client = RESTClient("https://example.com:8080")

        # Check all required methods exist
        assert hasattr(client, "send_message")
        assert hasattr(client, "send_streaming_message")
        assert hasattr(client, "get_task")
        assert hasattr(client, "cancel_task")
        assert hasattr(client, "subscribe_to_task")
        assert hasattr(client, "get_agent_card")
        assert hasattr(client, "close")

    def test_transport_type_is_rest(self):
        """Test transport type is correctly set to REST."""
        client = RESTClient("https://example.com:8080")
        assert client.transport_type == TransportType.REST

    def test_supports_streaming(self):
        """Test REST client reports streaming support."""
        client = RESTClient("https://example.com:8080")
        assert client.supports_streaming() is True
        assert client.supports_bidirectional_streaming() is False

    def test_get_transport_info(self):
        """Test transport info provides correct details."""
        client = RESTClient("https://example.com:8080", timeout=45.0)
        info = client.get_transport_info()

        assert info["transport_type"] == "rest"
        assert info["base_url"] == "https://example.com:8080/"
        assert info["timeout"] == 45.0
        assert info["supports_streaming"] is True
        assert info["supports_bidirectional"] is False
        assert info["streaming_mechanism"] == "Server-Sent Events (SSE)"

    def test_supports_list_tasks_method(self):
        """Test REST client supports list_tasks method."""
        client = RESTClient("https://example.com:8080")
        assert client.supports_method("list_tasks") is True


@pytest.mark.core
class TestRESTClientHttpClients:
    """Test HTTP client creation and management."""

    @patch("tck.transport.rest_client.Client")
    def test_client_creation(self, mock_client_class):
        """Test synchronous HTTP client creation."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = RESTClient("https://example.com:8080")
        http_client = client.client

        mock_client_class.assert_called_once_with(timeout=30.0, headers=client.default_headers, follow_redirects=True)
        assert http_client == mock_client

    @patch("tck.transport.rest_client.AsyncClient")
    def test_async_client_creation(self, mock_async_client_class):
        """Test asynchronous HTTP client creation."""
        mock_async_client = Mock()
        mock_async_client_class.return_value = mock_async_client

        client = RESTClient("https://example.com:8080")
        async_client = client.async_client

        mock_async_client_class.assert_called_once_with(timeout=30.0, headers=client.default_headers, follow_redirects=True)
        assert async_client == mock_async_client

    def test_client_caching(self):
        """Test HTTP clients are cached and reused."""
        with patch("tck.transport.rest_client.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            # First access creates client
            client1 = client.client
            assert mock_client_class.call_count == 1

            # Second access reuses client
            client2 = client.client
            assert mock_client_class.call_count == 1  # Not called again
            assert client1 == client2

    def test_close_cleans_up_clients(self):
        """Test close() properly cleans up HTTP clients."""
        with patch("tck.transport.rest_client.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            # Create client
            _ = client.client
            assert client._client is not None

            # Close should cleanup
            client.close()
            mock_client.close.assert_called_once()
            assert client._client is None

    def test_context_manager(self):
        """Test client works as context manager."""
        with patch("tck.transport.rest_client.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            with RESTClient("https://example.com:8080") as client:
                _ = client.client  # Trigger client creation

            # Should auto-close on exit
            mock_client.close.assert_called_once()


@pytest.mark.core
class TestRESTClientSendMessage:
    """Test send_message method for REST transport."""

    @patch("httpx.Client.post")
    def test_send_message_success(self, mock_post):
        """Test successful message sending via REST."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "task": {
                "id": "task-123",
                "context_id": "test-context",
                "status": {
                    "state": "TASK_STATE_SUBMITTED",
                    "message": {
                        "kind": "message",
                        "message_id": "response-123",
                        "role": "ROLE_AGENT",
                        "content": [{"text": "Message received via REST"}],
                    },
                },
            }
        }
        mock_post.return_value = mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.post = mock_post
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            message = {
                "message_id": "test-msg-1",
                "context_id": "test-context",
                "role": "user",
                "content": [{"text": "Hello via REST"}],
            }

            result = client.send_message(message)

            # Verify correct URL and payload were used
            mock_post.assert_called_once_with(
                "https://example.com:8080/v1/message:send", json={"message": message}, headers=client.default_headers
            )

            # Verify result
            assert result["task"]["id"] == "task-123"
            assert result["task"]["context_id"] == "test-context"

    @patch("httpx.Client.post")
    def test_send_message_with_extra_headers(self, mock_post):
        """Test send_message with extra headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"task": {"id": "task-123"}}
        mock_post.return_value = mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.post = mock_post
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            message = {"message_id": "test-msg-1", "content": [{"text": "Test"}]}
            extra_headers = {"Authorization": "Bearer token123"}

            client.send_message(message, extra_headers=extra_headers)

            # Verify headers were merged
            expected_headers = client.default_headers.copy()
            expected_headers.update(extra_headers)

            mock_post.assert_called_once_with(
                "https://example.com:8080/v1/message:send", json={"message": message}, headers=expected_headers
            )

    @patch("httpx.Client.post")
    def test_send_message_with_config_options(self, mock_post):
        """Test send_message with configuration options."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"task": {"id": "task-123"}}
        mock_post.return_value = mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.post = mock_post
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            message = {"message_id": "test-msg-1", "content": [{"text": "Test"}]}

            client.send_message(message, accepted_output_modes=["text", "json"], history_length=5, blocking=True)

            # Verify payload includes config options
            expected_payload = {
                "message": message,
                "accepted_output_modes": ["text", "json"],
                "history_length": 5,
                "blocking": True,
            }

            mock_post.assert_called_once_with(
                "https://example.com:8080/v1/message:send", json=expected_payload, headers=client.default_headers
            )

    @patch("httpx.Client.post")
    def test_send_message_with_http_error(self, mock_post):
        """Test send_message handles HTTP errors properly."""
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.post = mock_post
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            message = {"message_id": "test-msg-1", "content": [{"text": "Test"}]}

            with pytest.raises(TransportError) as exc_info:
                client.send_message(message)

            assert "REST transport error" in str(exc_info.value)
            assert "HTTP 400" in str(exc_info.value)

    @patch("httpx.Client.post")
    def test_send_message_with_request_error(self, mock_post):
        """Test send_message handles request errors."""
        import httpx

        mock_post.side_effect = httpx.RequestError("Connection failed")

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.post = mock_post
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            message = {"message_id": "test-msg-1", "content": [{"text": "Test"}]}

            with pytest.raises(TransportError) as exc_info:
                client.send_message(message)

            assert "REST transport error" in str(exc_info.value)
            assert "HTTP request failed" in str(exc_info.value)


@pytest.mark.core
class TestRESTClientStreamingMessage:
    """Test send_streaming_message method for REST transport."""

    @patch("tck.transport.rest_client.AsyncClient")
    @pytest.mark.asyncio
    async def test_send_streaming_message_success(self, mock_async_client_class):
        """Test successful streaming message via REST."""
        # Mock SSE response lines
        sse_lines = [
            'data: {"task": {"id": "task-stream-1", "status": {"state": "TASK_STATE_SUBMITTED"}}}',
            "",
            'data: {"status_update": {"task_id": "task-stream-1", "status": {"state": "TASK_STATE_WORKING"}}}',
            "",
            'data: {"status_update": {"task_id": "task-stream-1", "status": {"state": "TASK_STATE_COMPLETED"}, "final": true}}',
            "",
            "data: [DONE]",
        ]

        # Create async iterator for lines
        async def async_iter_lines():
            for line in sse_lines:
                yield line

        # Mock async context manager for streaming
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = async_iter_lines

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)

        mock_async_client = Mock()
        mock_async_client.stream.return_value = mock_stream_context
        mock_async_client_class.return_value = mock_async_client

        client = RESTClient("https://example.com:8080")
        client._async_client = mock_async_client  # Set directly to bypass property

        message = {"message_id": "stream-msg-1", "context_id": "stream-context", "content": [{"text": "Hello streaming REST"}]}

        responses = []
        async for response in client.send_streaming_message(message):
            responses.append(response)

        # Verify we got expected streaming responses
        assert len(responses) == 3

        # First response should be initial task
        assert "task" in responses[0]
        assert responses[0]["task"]["id"] == "task-stream-1"

        # Subsequent responses should be status updates
        assert "status_update" in responses[1]
        assert responses[1]["status_update"]["status"]["state"] == "TASK_STATE_WORKING"

        assert "status_update" in responses[2]
        assert responses[2]["status_update"]["status"]["state"] == "TASK_STATE_COMPLETED"
        assert responses[2]["status_update"]["final"] is True

        # Verify correct URL and headers were used
        mock_async_client.stream.assert_called_once_with(
            "POST",
            "https://example.com:8080/v1/message:stream",
            json={"message": message},
            headers={**client.default_headers, "Accept": "text/event-stream"},
        )

    @patch("tck.transport.rest_client.AsyncClient")
    @pytest.mark.asyncio
    async def test_send_streaming_message_with_http_error(self, mock_async_client_class):
        """Test streaming message handles HTTP errors."""
        # Mock HTTP error response
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.aread = AsyncMock(return_value=b"Internal Server Error")

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)

        mock_async_client = Mock()
        mock_async_client.stream.return_value = mock_stream_context
        mock_async_client_class.return_value = mock_async_client

        client = RESTClient("https://example.com:8080")
        client._async_client = mock_async_client  # Set directly to bypass property

        message = {"message_id": "stream-msg-1", "content": [{"text": "Test"}]}

        with pytest.raises(TransportError) as exc_info:
            async for _ in client.send_streaming_message(message):
                pass

        assert "REST streaming error" in str(exc_info.value)
        assert "HTTP 500" in str(exc_info.value)

    @patch("tck.transport.rest_client.AsyncClient")
    @pytest.mark.asyncio
    async def test_send_streaming_message_invalid_sse_data(self, mock_async_client_class):
        """Test streaming message handles invalid SSE data gracefully."""
        # Mock SSE response with invalid JSON
        sse_lines = [
            'data: {"task": {"id": "task-1"}}',  # Valid
            "data: invalid-json",  # Invalid - should be skipped
            'data: {"status_update": {"task_id": "task-1", "final": true}}',  # Valid
            "data: [DONE]",
        ]

        # Create async iterator for lines
        async def async_iter_lines():
            for line in sse_lines:
                yield line

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = async_iter_lines

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)

        mock_async_client = Mock()
        mock_async_client.stream.return_value = mock_stream_context
        mock_async_client_class.return_value = mock_async_client

        client = RESTClient("https://example.com:8080")
        client._async_client = mock_async_client  # Set directly to bypass property

        message = {"message_id": "stream-msg-1", "content": [{"text": "Test"}]}

        responses = []
        async for response in client.send_streaming_message(message):
            responses.append(response)

        # Should get 2 valid responses (invalid JSON skipped)
        assert len(responses) == 2
        assert "task" in responses[0]
        assert "status_update" in responses[1]


@pytest.mark.core
class TestRESTClientTaskOperations:
    """Test task-related REST operations."""

    @patch("httpx.Client.get")
    def test_get_task_success(self, mock_get):
        """Test successful task retrieval via REST."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "task-123",
            "context_id": "default-context",
            "status": {
                "state": "TASK_STATE_COMPLETED",
                "message": {
                    "kind": "message",
                    "message_id": "status-123",
                    "role": "ROLE_AGENT",
                    "content": [{"text": "Task 123 retrieved via REST"}],
                },
            },
        }
        mock_get.return_value = mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get = mock_get
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            result = client.get_task("task-123")

            mock_get.assert_called_once_with("https://example.com:8080/v1/tasks/task-123", params={}, headers=client.default_headers)

            assert result["id"] == "task-123"
            assert result["context_id"] == "default-context"
            assert result["status"]["state"] == "TASK_STATE_COMPLETED"

    @patch("httpx.Client.get")
    def test_get_task_with_history_length(self, mock_get):
        """Test get_task with history_length parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "task-123"}
        mock_get.return_value = mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get = mock_get
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            client.get_task("task-123", history_length=10)

            mock_get.assert_called_once_with(
                "https://example.com:8080/v1/tasks/task-123", params={"history_length": 10}, headers=client.default_headers
            )

    @patch("httpx.Client.post")
    def test_cancel_task_success(self, mock_post):
        """Test successful task cancellation via REST."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "task-456",
            "status": {
                "state": "TASK_STATE_CANCELLED",
                "message": {
                    "kind": "message",
                    "message_id": "cancel-456",
                    "role": "ROLE_AGENT",
                    "content": [{"text": "Task 456 cancelled via REST"}],
                },
            },
        }
        mock_post.return_value = mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.post = mock_post
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            result = client.cancel_task("task-456")

            mock_post.assert_called_once_with("https://example.com:8080/v1/tasks/task-456:cancel", headers=client.default_headers)

            assert result["id"] == "task-456"
            assert result["status"]["state"] == "TASK_STATE_CANCELLED"

    @patch("tck.transport.rest_client.AsyncClient")
    @pytest.mark.asyncio
    async def test_subscribe_to_task_success(self, mock_async_client_class):
        """Test successful task subscription via REST."""
        # Mock SSE response for task subscription
        sse_lines = [
            'data: {"task": {"id": "task-789", "status": {"state": "TASK_STATE_WORKING"}}}',
            "",
            'data: {"status_update": {"task_id": "task-789", "status": {"state": "TASK_STATE_COMPLETED"}, "final": true}}',
            "",
            "data: [DONE]",
        ]

        # Create async iterator for lines
        async def async_iter_lines():
            for line in sse_lines:
                yield line

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = async_iter_lines

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)

        mock_async_client = Mock()
        mock_async_client.stream.return_value = mock_stream_context
        mock_async_client_class.return_value = mock_async_client

        client = RESTClient("https://example.com:8080")
        client._async_client = mock_async_client  # Set directly to bypass property

        events = []
        async for event in client.subscribe_to_task("task-789"):
            events.append(event)

        assert len(events) == 2

        # First event should be current task state
        assert "task" in events[0]
        assert events[0]["task"]["id"] == "task-789"

        # Second event should be status update
        assert "status_update" in events[1]
        assert events[1]["status_update"]["task_id"] == "task-789"
        assert events[1]["status_update"]["final"] is True

        # Verify correct URL and headers were used
        mock_async_client.stream.assert_called_once_with(
            "GET",
            "https://example.com:8080/v1/tasks/task-789:subscribe",
            headers={**client.default_headers, "Accept": "text/event-stream"},
        )


@pytest.mark.core
class TestRESTClientAgentCard:
    """Test agent card retrieval via REST."""

    @patch("httpx.Client.get")
    def test_get_agent_card_success(self, mock_get):
        """Test successful agent card retrieval via REST."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "protocol_version": "0.3.0",
            "name": "A2A REST Test Agent",
            "description": "Test agent accessed via REST transport",
            "url": "https://example.com:8080/",
            "preferred_transport": "REST",
            "capabilities": {"streaming": True, "push_notifications": False},
            "additional_interfaces": [{"url": "https://example.com:8080/", "transport": "REST"}],
        }
        mock_get.return_value = mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get = mock_get
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            result = client.get_agent_card()

            mock_get.assert_called_once_with("https://example.com:8080/v1/card", headers=client.default_headers)

            assert result["protocol_version"] == "0.3.0"
            assert result["name"] == "A2A REST Test Agent"
            assert result["preferred_transport"] == "REST"
            assert result["capabilities"]["streaming"] is True

    @patch("httpx.Client.get")
    def test_get_authenticated_extended_card_success(self, mock_get):
        """Test successful authenticated extended agent card retrieval via REST."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "protocol_version": "0.3.0",
            "name": "A2A REST Test Agent (Extended)",
            "description": "Extended test agent accessed via REST transport with authentication",
            "url": "https://example.com:8080/",
            "preferred_transport": "REST",
            "capabilities": {"streaming": True, "push_notifications": True, "authenticated_features": True},
            "security_schemes": {"bearer": {"type": "http", "scheme": "bearer"}},
            "extended_metadata": {"internal_version": "1.2.3", "deployment_info": "production"},
        }
        mock_get.return_value = mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get = mock_get
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            auth_headers = {"Authorization": "Bearer token123"}
            result = client.get_authenticated_extended_card(extra_headers=auth_headers)

            expected_headers = client.default_headers.copy()
            expected_headers.update(auth_headers)

            mock_get.assert_called_once_with("https://example.com:8080/v1/card", headers=expected_headers)

            assert result["name"] == "A2A REST Test Agent (Extended)"
            assert result["capabilities"]["authenticated_features"] is True
            assert "security_schemes" in result
            assert "extended_metadata" in result


@pytest.mark.core
class TestRESTClientPushNotifications:
    """Test push notification configuration methods."""

    @patch("httpx.Client.post")
    def test_set_push_notification_config_success(self, mock_post):
        """Test successful push notification config creation via REST."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "name": "tasks/task-123/push-notification-configs/config1",
            "push_notification_config": {
                "id": "config1",
                "url": "https://webhook.example.com/notify",
                "token": "webhook-token-123",
            },
        }
        mock_post.return_value = mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.post = mock_post
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            config = {"id": "config1", "url": "https://webhook.example.com/notify", "token": "webhook-token-123"}

            result = client.set_push_notification_config("task-123", config)

            mock_post.assert_called_once_with(
                "https://example.com:8080/v1/tasks/task-123/pushNotificationConfigs", json=config, headers=client.default_headers
            )

            assert result["push_notification_config"]["id"] == "config1"
            assert result["push_notification_config"]["url"] == "https://webhook.example.com/notify"

    @patch("httpx.Client.get")
    def test_get_push_notification_config_success(self, mock_get):
        """Test successful push notification config retrieval via REST."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "tasks/task-123/pushNotificationConfigs/config1",
            "push_notification_config": {
                "id": "config1",
                "url": "https://webhook.example.com/notify",
                "token": "webhook-token-123",
            },
        }
        mock_get.return_value = mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get = mock_get
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            result = client.get_push_notification_config("task-123", "config1")

            mock_get.assert_called_once_with(
                "https://example.com:8080/v1/tasks/task-123/pushNotificationConfigs/config1", headers=client.default_headers
            )

            assert result["push_notification_config"]["id"] == "config1"

    @patch("httpx.Client.get")
    def test_list_push_notification_configs_success(self, mock_get):
        """Test successful push notification configs listing via REST."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "configs": [
                {
                    "name": "tasks/task-123/pushNotificationConfigs/config1",
                    "push_notification_config": {"id": "config1", "url": "https://webhook1.example.com/notify"},
                },
                {
                    "name": "tasks/task-123/pushNotificationConfigs/config2",
                    "push_notification_config": {"id": "config2", "url": "https://webhook2.example.com/notify"},
                },
            ],
            "next_page_token": "",
        }
        mock_get.return_value = mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get = mock_get
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            result = client.list_push_notification_configs("task-123")

            mock_get.assert_called_once_with(
                "https://example.com:8080/v1/tasks/task-123/pushNotificationConfigs", headers=client.default_headers
            )

            assert len(result["configs"]) == 2
            assert result["configs"][0]["push_notification_config"]["id"] == "config1"
            assert result["configs"][1]["push_notification_config"]["id"] == "config2"

    @patch("httpx.Client.delete")
    def test_delete_push_notification_config_success(self, mock_delete):
        """Test successful push notification config deletion via REST."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.content = b""  # Empty response for successful deletion
        mock_delete.return_value = mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.delete = mock_delete
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            result = client.delete_push_notification_config("task-123", "config1")

            mock_delete.assert_called_once_with(
                "https://example.com:8080/v1/tasks/task-123/pushNotificationConfigs/config1", headers=client.default_headers
            )

            assert result == {}  # Empty response for successful deletion


@pytest.mark.core
class TestRESTClientListTasks:
    """Test list_tasks method (REST-specific)."""

    @patch("httpx.Client.get")
    def test_list_tasks_success(self, mock_get):
        """Test successful tasks listing via REST."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tasks": [
                {"id": "task-1", "context_id": "context-1", "status": {"state": "TASK_STATE_COMPLETED"}},
                {"id": "task-2", "context_id": "context-2", "status": {"state": "TASK_STATE_WORKING"}},
            ],
            "next_page_token": "",
        }
        mock_get.return_value = mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get = mock_get
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            result = client.list_tasks()

            mock_get.assert_called_once_with("https://example.com:8080/tasks", params={}, headers=client.default_headers)

            assert len(result["tasks"]) == 2
            assert result["tasks"][0]["id"] == "task-1"
            assert result["tasks"][1]["id"] == "task-2"

    @patch("httpx.Client.get")
    def test_list_tasks_with_pagination(self, mock_get):
        """Test tasks listing with pagination parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tasks": [], "next_page_token": ""}
        mock_get.return_value = mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get = mock_get
            mock_client_class.return_value = mock_client

            client = RESTClient("https://example.com:8080")

            client.list_tasks(page_size=10, page_token="token123", filter="completed")

            mock_get.assert_called_once_with(
                "https://example.com:8080/tasks",
                params={"page_size": 10, "page_token": "token123", "filter": "completed"},
                headers=client.default_headers,
            )


# Integration-style tests for interface compatibility


@pytest.mark.core
def test_rest_client_interface_compatibility():
    """Test RESTClient maintains interface compatibility with BaseTransportClient."""
    from tck.transport.base_client import BaseTransportClient

    client = RESTClient("https://example.com:8080")

    # Should be instance of base class
    assert isinstance(client, BaseTransportClient)

    # Should have correct transport type
    assert client.transport_type == TransportType.REST

    # Should implement all required methods
    required_methods = [
        "send_message",
        "send_streaming_message",
        "get_task",
        "cancel_task",
        "subscribe_to_task",
        "get_agent_card",
        "get_authenticated_extended_card",
        "set_push_notification_config",
        "get_push_notification_config",
        "list_push_notification_configs",
        "delete_push_notification_config",
    ]

    for method_name in required_methods:
        assert hasattr(client, method_name)
        assert callable(getattr(client, method_name))


@pytest.mark.core
def test_rest_client_configuration_options():
    """Test RESTClient handles various configuration options."""
    # Test with different URL formats
    clients = [
        RESTClient("http://example.com:8080"),
        RESTClient("https://secure.example.com:8080"),
        RESTClient("https://example.com:8080/"),  # With trailing slash
        RESTClient("https://example.com"),  # Without port
    ]

    for client in clients:
        assert client.transport_type == TransportType.REST
        assert client.base_url.endswith("/")
        assert client.timeout > 0
        assert "Content-Type" in client.default_headers
        assert client.default_headers["Content-Type"] == "application/json"

    # Test custom timeout
    client_custom = RESTClient("https://example.com:8080", timeout=120.0)
    assert client_custom.timeout == 120.0
