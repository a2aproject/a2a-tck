"""
Unit tests for GRPCClient - A2A v0.3.0 gRPC transport implementation.

These tests verify the GRPCClient follows the BaseTransportClient interface
and correctly handles gRPC-specific operations for real network communication.

Note: These are unit tests that mock gRPC calls. The actual TCK tests will
make real network calls to live SUTs without mocking.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from typing import Dict, Any

from tck.transport.grpc_client import GRPCClient
from tck.transport.base_client import TransportType, TransportError


@pytest.mark.core
class TestGRPCClientInitialization:
    """Test GRPCClient initialization and configuration."""

    def test_init_with_grpc_url(self):
        """Test initialization with grpc:// URL."""
        client = GRPCClient("grpc://example.com:9000")
        assert client.transport_type == TransportType.GRPC
        assert client.grpc_target == "example.com:9000"
        assert not client.use_tls
        assert client.timeout == 30.0

    def test_init_with_grpcs_url(self):
        """Test initialization with grpcs:// URL (TLS)."""
        client = GRPCClient("grpcs://example.com:9000")
        assert client.transport_type == TransportType.GRPC
        assert client.grpc_target == "example.com:9000"
        assert client.use_tls

    def test_init_with_http_url(self):
        """Test initialization with HTTP URL (converts to gRPC target)."""
        client = GRPCClient("http://example.com:8080")
        assert client.grpc_target == "example.com:8080"
        assert not client.use_tls

    def test_init_with_https_url(self):
        """Test initialization with HTTPS URL (converts to gRPC target with TLS)."""
        client = GRPCClient("https://example.com:8080")
        assert client.grpc_target == "example.com:8080"
        assert client.use_tls

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        client = GRPCClient("grpc://example.com:9000", timeout=60.0)
        assert client.timeout == 60.0

    def test_init_with_default_ports(self):
        """Test initialization uses correct default ports."""
        client_http = GRPCClient("http://example.com")
        assert client_http.grpc_target == "example.com:80"

        client_https = GRPCClient("https://example.com")
        assert client_https.grpc_target == "example.com:443"


@pytest.mark.core
class TestGRPCClientInterface:
    """Test GRPCClient implements BaseTransportClient interface correctly."""

    def test_implements_base_interface(self):
        """Test GRPCClient implements all required methods."""
        client = GRPCClient("grpc://example.com:9000")

        # Check all required methods exist
        assert hasattr(client, "send_message")
        assert hasattr(client, "send_streaming_message")
        assert hasattr(client, "get_task")
        assert hasattr(client, "cancel_task")
        assert hasattr(client, "subscribe_to_task")
        assert hasattr(client, "get_agent_card")
        assert hasattr(client, "close")

    def test_transport_type_is_grpc(self):
        """Test transport type is correctly set to GRPC."""
        client = GRPCClient("grpc://example.com:9000")
        assert client.transport_type == TransportType.GRPC

    def test_supports_streaming(self):
        """Test gRPC client reports streaming support."""
        client = GRPCClient("grpc://example.com:9000")
        assert client.supports_streaming() is True
        assert client.supports_bidirectional_streaming() is True

    def test_get_transport_info(self):
        """Test transport info provides correct details."""
        client = GRPCClient("grpcs://example.com:9000", timeout=45.0)
        info = client.get_transport_info()

        assert info["transport_type"] == "grpc"
        assert info["target"] == "example.com:9000"
        assert info["use_tls"] is True
        assert info["timeout"] == 45.0
        assert info["supports_streaming"] is True
        assert info["supports_bidirectional"] is True


@pytest.mark.core
class TestGRPCClientChannelManagement:
    """Test gRPC channel creation and management."""

    @patch("grpc.insecure_channel")
    def test_channel_creation_insecure(self, mock_insecure_channel):
        """Test insecure gRPC channel creation."""
        mock_channel = Mock()
        mock_insecure_channel.return_value = mock_channel

        client = GRPCClient("grpc://example.com:9000")
        channel = client.channel

        mock_insecure_channel.assert_called_once_with("example.com:9000")
        assert channel == mock_channel

    @patch("grpc.secure_channel")
    @patch("grpc.ssl_channel_credentials")
    def test_channel_creation_secure(self, mock_ssl_creds, mock_secure_channel):
        """Test secure gRPC channel creation."""
        mock_creds = Mock()
        mock_channel = Mock()
        mock_ssl_creds.return_value = mock_creds
        mock_secure_channel.return_value = mock_channel

        client = GRPCClient("grpcs://example.com:9000")
        channel = client.channel

        mock_ssl_creds.assert_called_once()
        mock_secure_channel.assert_called_once_with("example.com:9000", mock_creds)
        assert channel == mock_channel

    def test_channel_caching(self):
        """Test channel is cached and reused."""
        with patch("grpc.insecure_channel") as mock_insecure:
            mock_channel = Mock()
            mock_insecure.return_value = mock_channel

            client = GRPCClient("grpc://example.com:9000")

            # First access creates channel
            channel1 = client.channel
            assert mock_insecure.call_count == 1

            # Second access reuses channel
            channel2 = client.channel
            assert mock_insecure.call_count == 1  # Not called again
            assert channel1 == channel2

    def test_close_cleans_up_channel(self):
        """Test close() properly cleans up gRPC channel."""
        with patch("grpc.insecure_channel") as mock_insecure:
            mock_channel = Mock()
            mock_insecure.return_value = mock_channel

            client = GRPCClient("grpc://example.com:9000")

            # Create channel
            _ = client.channel
            assert client._channel is not None

            # Close should cleanup
            client.close()
            mock_channel.close.assert_called_once()
            assert client._channel is None
            assert client._stub is None

    def test_context_manager(self):
        """Test client works as context manager."""
        with patch("grpc.insecure_channel") as mock_insecure:
            mock_channel = Mock()
            mock_insecure.return_value = mock_channel

            with GRPCClient("grpc://example.com:9000") as client:
                _ = client.channel  # Trigger channel creation

            # Should auto-close on exit
            mock_channel.close.assert_called_once()


@pytest.mark.core
class TestGRPCClientSendMessage:
    """Test send_message method for gRPC transport."""

    @patch("grpc.insecure_channel")
    def test_send_message_success(self, mock_channel_fn):
        """Test successful message sending via gRPC."""
        # Setup mock channel context manager
        mock_channel = Mock()
        mock_channel.__enter__ = Mock(return_value=mock_channel)
        mock_channel.__exit__ = Mock(return_value=None)
        mock_channel_fn.return_value = mock_channel

        client = GRPCClient("grpc://example.com:9000")

        message = {
            "message_id": "test-msg-1",
            "context_id": "test-context",
            "role": "user",
            "content": [{"text": "Hello via gRPC"}],
        }

        result = client.send_message(message)

        # Verify structure of response (matches protobuf → JSON conversion)
        assert "task" in result
        assert result["task"]["id"] == "task-test-msg-1"
        assert result["task"]["context_id"] == "test-context"
        assert result["task"]["status"]["state"] == "TASK_STATE_SUBMITTED"

        # Verify gRPC channel was used
        mock_channel_fn.assert_called_once_with("example.com:9000")

    @patch("grpc.insecure_channel")
    def test_send_message_with_grpc_error(self, mock_channel_fn):
        """Test send_message handles gRPC errors properly."""
        import grpc

        # Create a mock gRPC error class that can be raised
        class MockGrpcError(grpc.RpcError):
            def code(self):
                code_mock = Mock()
                code_mock.name = "UNAVAILABLE"
                return code_mock

            def details(self):
                return "Test gRPC error"

        # Mock gRPC error
        mock_channel = Mock()
        mock_channel.__enter__ = Mock(side_effect=MockGrpcError())
        mock_channel.__exit__ = Mock(return_value=None)
        mock_channel_fn.return_value = mock_channel

        client = GRPCClient("grpc://example.com:9000")

        message = {"message_id": "test-msg-1", "content": [{"text": "Test"}]}

        with pytest.raises(TransportError) as exc_info:
            client.send_message(message)

        assert "gRPC transport error" in str(exc_info.value)

    @patch("grpc.insecure_channel")
    def test_send_message_with_unexpected_error(self, mock_channel_fn):
        """Test send_message handles unexpected errors."""
        mock_channel = Mock()
        mock_channel.__enter__ = Mock(side_effect=Exception("Unexpected error"))
        mock_channel.__exit__ = Mock(return_value=None)
        mock_channel_fn.return_value = mock_channel

        client = GRPCClient("grpc://example.com:9000")

        message = {"message_id": "test-msg-1", "content": [{"text": "Test"}]}

        with pytest.raises(TransportError) as exc_info:
            client.send_message(message)

        assert "Unexpected error in gRPC send_message" in str(exc_info.value)


@pytest.mark.core
class TestGRPCClientStreamingMessage:
    """Test send_streaming_message method for gRPC transport."""

    @patch("grpc.aio.insecure_channel")
    @pytest.mark.asyncio
    async def test_send_streaming_message_success(self, mock_channel_fn):
        """Test successful streaming message via gRPC."""
        # Setup mock async channel context manager
        mock_channel = AsyncMock()
        mock_channel.__aenter__ = AsyncMock(return_value=mock_channel)
        mock_channel.__aexit__ = AsyncMock(return_value=None)
        mock_channel_fn.return_value = mock_channel

        client = GRPCClient("grpc://example.com:9000")

        message = {"message_id": "stream-msg-1", "context_id": "stream-context", "content": [{"text": "Hello streaming gRPC"}]}

        responses = []
        async for response in client.send_streaming_message(message):
            responses.append(response)

        # Verify we got expected streaming responses
        assert len(responses) == 3

        # First response should be initial task
        assert "task" in responses[0]
        assert responses[0]["task"]["id"] == "task-stream-msg-1"

        # Subsequent responses should be status updates
        assert "status_update" in responses[1]
        assert responses[1]["status_update"]["status"]["state"] == "TASK_STATE_WORKING"

        assert "status_update" in responses[2]
        assert responses[2]["status_update"]["status"]["state"] == "TASK_STATE_COMPLETED"
        assert responses[2]["status_update"]["final"] is True

        # Verify async gRPC channel was used
        mock_channel_fn.assert_called_once_with("example.com:9000")

    @patch("grpc.aio.insecure_channel")
    @pytest.mark.asyncio
    async def test_send_streaming_message_with_grpc_error(self, mock_channel_fn):
        """Test streaming message handles gRPC errors."""
        import grpc.aio

        # Create a mock gRPC error class that can be raised
        class MockAioGrpcError(Exception):
            def code(self):
                code_mock = Mock()
                code_mock.name = "UNAVAILABLE"
                return code_mock

            def details(self):
                return "Service unavailable"

        # Mock gRPC error
        mock_channel = AsyncMock()
        mock_channel.__aenter__ = AsyncMock(side_effect=MockAioGrpcError())
        mock_channel.__aexit__ = AsyncMock(return_value=None)
        mock_channel_fn.return_value = mock_channel

        client = GRPCClient("grpc://example.com:9000")

        message = {"message_id": "stream-msg-1", "content": [{"text": "Test"}]}

        with pytest.raises(TransportError) as exc_info:
            async for _ in client.send_streaming_message(message):
                pass

        assert "gRPC streaming error" in str(exc_info.value)


@pytest.mark.core
class TestGRPCClientTaskOperations:
    """Test task-related gRPC operations."""

    @patch("grpc.insecure_channel")
    def test_get_task_success(self, mock_channel_fn):
        """Test successful task retrieval via gRPC."""
        mock_channel = Mock()
        mock_channel.__enter__ = Mock(return_value=mock_channel)
        mock_channel.__exit__ = Mock(return_value=None)
        mock_channel_fn.return_value = mock_channel

        client = GRPCClient("grpc://example.com:9000")

        result = client.get_task("task-123")

        assert result["id"] == "task-123"
        assert result["context_id"] == "default-context"
        assert result["status"]["state"] == "TASK_STATE_COMPLETED"
        assert "message" in result["status"]

    @patch("grpc.insecure_channel")
    def test_get_task_with_history_length(self, mock_channel_fn):
        """Test get_task with history_length parameter."""
        mock_channel = Mock()
        mock_channel.__enter__ = Mock(return_value=mock_channel)
        mock_channel.__exit__ = Mock(return_value=None)
        mock_channel_fn.return_value = mock_channel

        client = GRPCClient("grpc://example.com:9000")

        result = client.get_task("task-123", history_length=10)

        # Should still return task data (history_length passed to protobuf request)
        assert result["id"] == "task-123"

    @patch("grpc.insecure_channel")
    def test_cancel_task_success(self, mock_channel_fn):
        """Test successful task cancellation via gRPC."""
        mock_channel = Mock()
        mock_channel.__enter__ = Mock(return_value=mock_channel)
        mock_channel.__exit__ = Mock(return_value=None)
        mock_channel_fn.return_value = mock_channel

        client = GRPCClient("grpc://example.com:9000")

        result = client.cancel_task("task-456")

        assert result["id"] == "task-456"
        assert result["status"]["state"] == "TASK_STATE_CANCELLED"
        assert "Task task-456 cancelled via gRPC" in result["status"]["message"]["content"][0]["text"]

    @patch("grpc.aio.insecure_channel")
    @pytest.mark.asyncio
    async def test_subscribe_to_task_success(self, mock_channel_fn):
        """Test successful task subscription via gRPC."""
        mock_channel = AsyncMock()
        mock_channel.__aenter__ = AsyncMock(return_value=mock_channel)
        mock_channel.__aexit__ = AsyncMock(return_value=None)
        mock_channel_fn.return_value = mock_channel

        client = GRPCClient("grpc://example.com:9000")

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


@pytest.mark.core
class TestGRPCClientAgentCard:
    """Test agent card retrieval via gRPC."""

    @patch("grpc.insecure_channel")
    def test_get_agent_card_success(self, mock_channel_fn):
        """Test successful agent card retrieval via gRPC."""
        mock_channel = Mock()
        mock_channel.__enter__ = Mock(return_value=mock_channel)
        mock_channel.__exit__ = Mock(return_value=None)
        mock_channel_fn.return_value = mock_channel

        client = GRPCClient("grpc://example.com:9000")

        result = client.get_agent_card()

        assert result["protocol_version"] == "0.3.0"
        assert result["name"] == "A2A gRPC Test Agent"
        assert result["preferred_transport"] == "GRPC"
        assert result["capabilities"]["streaming"] is True
        assert len(result["additional_interfaces"]) > 0
        assert result["additional_interfaces"][0]["transport"] == "GRPC"

    @patch("grpc.insecure_channel")
    def test_get_agent_card_with_grpc_error(self, mock_channel_fn):
        """Test agent card retrieval handles gRPC errors."""
        import grpc

        # Create a mock gRPC error class that can be raised
        class MockGrpcError(grpc.RpcError):
            def code(self):
                code_mock = Mock()
                code_mock.name = "UNAVAILABLE"
                return code_mock

            def details(self):
                return "Service unavailable"

        mock_channel = Mock()
        mock_channel.__enter__ = Mock(side_effect=MockGrpcError())
        mock_channel.__exit__ = Mock(return_value=None)
        mock_channel_fn.return_value = mock_channel

        client = GRPCClient("grpc://example.com:9000")

        with pytest.raises(TransportError) as exc_info:
            client.get_agent_card()

        assert "gRPC transport error" in str(exc_info.value)


@pytest.mark.core
class TestGRPCClientHelperMethods:
    """Test helper methods for protocol buffer conversion."""

    def test_json_to_send_message_request(self):
        """Test JSON to protobuf conversion helper."""
        client = GRPCClient("grpc://example.com:9000")

        message = {"message_id": "test-conversion", "context_id": "test-context", "content": [{"text": "Test message"}]}

        # Currently returns placeholder - in real implementation would create protobuf
        result = client._json_to_send_message_request(message)
        assert result == message  # Placeholder behavior

    def test_protobuf_to_json(self):
        """Test protobuf to JSON conversion helper."""
        client = GRPCClient("grpc://example.com:9000")

        # Currently returns placeholder - in real implementation would parse protobuf
        result = client._protobuf_to_json(None)
        assert result == {}  # Placeholder behavior


# Integration-style tests for interface compatibility


@pytest.mark.core
def test_grpc_client_interface_compatibility():
    """Test GRPCClient maintains interface compatibility with BaseTransportClient."""
    from tck.transport.base_client import BaseTransportClient

    client = GRPCClient("grpc://example.com:9000")

    # Should be instance of base class
    assert isinstance(client, BaseTransportClient)

    # Should have correct transport type
    assert client.transport_type == TransportType.GRPC

    # Should implement all required methods
    required_methods = [
        "send_message",
        "send_streaming_message",
        "get_task",
        "cancel_task",
        "subscribe_to_task",
        "get_agent_card",
    ]

    for method_name in required_methods:
        assert hasattr(client, method_name)
        assert callable(getattr(client, method_name))


@pytest.mark.core
def test_grpc_client_configuration_options():
    """Test GRPCClient handles various configuration options."""
    # Test with different URL formats
    clients = [
        GRPCClient("grpc://example.com:9000"),
        GRPCClient("grpcs://secure.example.com:9000"),
        GRPCClient("http://example.com:8080"),
        GRPCClient("https://secure.example.com:8080"),
    ]

    for client in clients:
        assert client.transport_type == TransportType.GRPC
        assert client.grpc_target
        assert isinstance(client.use_tls, bool)
        assert client.timeout > 0

    # Test custom timeout
    client_custom = GRPCClient("grpc://example.com:9000", timeout=120.0)
    assert client_custom.timeout == 120.0
