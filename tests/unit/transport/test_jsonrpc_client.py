"""
Integration tests for JSONRPCClient.

Note: These are integration tests that verify the client structure and interfaces,
but do not make actual network calls (since we need a real SUT for that).
The actual network functionality is tested in the TCK integration test suite.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from tck.transport.jsonrpc_client import JSONRPCClient, JSONRPCError
from tck.transport.base_client import TransportType


@pytest.mark.core
class TestJSONRPCClient:
    """Test cases for JSONRPCClient interface and structure."""

    def setup_method(self):
        """Set up test client."""
        self.client = JSONRPCClient("https://example.com/jsonrpc")

    def teardown_method(self):
        """Clean up after test."""
        self.client.close()

    def test_initialization(self):
        """Test JSONRPCClient initialization."""
        client = JSONRPCClient("https://example.com/jsonrpc", timeout=60.0, max_retries=5)

        assert client.base_url == "https://example.com/jsonrpc"
        assert client.transport_type == TransportType.JSON_RPC
        assert client.timeout == 60.0
        assert client.max_retries == 5
        assert client.session is not None

        client.close()

    def test_generate_id(self):
        """Test request ID generation."""
        id1 = self.client._generate_id()
        id2 = self.client._generate_id()

        assert id1.startswith("tck-")
        assert id2.startswith("tck-")
        assert id1 != id2  # Should be unique

    def test_transport_info(self):
        """Test transport information."""
        info = self.client.get_transport_info()

        assert info["transport_type"] == "jsonrpc"
        assert info["base_url"] == "https://example.com/jsonrpc"
        assert "send_message" in info["supported_methods"]
        assert "get_task" in info["supported_methods"]
        assert "cancel_task" in info["supported_methods"]

    def test_supports_method(self):
        """Test method support checking."""
        # Core methods should be supported
        assert self.client.supports_method("send_message") is True
        assert self.client.supports_method("get_task") is True
        assert self.client.supports_method("cancel_task") is True
        assert self.client.supports_method("resubscribe_task") is True

        # list_tasks is not supported by JSON-RPC transport
        assert self.client.supports_method("list_tasks") is False

        # Unknown methods should not be supported
        assert self.client.supports_method("unknown_method") is False

    @patch("requests.Session.post")
    def test_make_jsonrpc_request_success(self, mock_post):
        """Test successful JSON-RPC request structure."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"jsonrpc": "2.0", "result": {"taskId": "test-123"}, "id": "test-id"}'
        mock_response.json.return_value = {"jsonrpc": "2.0", "result": {"taskId": "test-123"}, "id": "test-id"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Make request
        result = self.client._make_jsonrpc_request("test/method", {"param": "value"}, "test-id")

        # Verify request structure
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        assert call_args[1]["json"]["jsonrpc"] == "2.0"
        assert call_args[1]["json"]["method"] == "test/method"
        assert call_args[1]["json"]["params"] == {"param": "value"}
        assert call_args[1]["json"]["id"] == "test-id"
        assert call_args[1]["headers"]["Content-Type"] == "application/json"

        # Verify result
        assert result == {"jsonrpc": "2.0", "result": {"taskId": "test-123"}, "id": "test-id"}

    @patch("requests.Session.post")
    def test_make_jsonrpc_request_error_response(self, mock_post):
        """Test JSON-RPC error response handling."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": "test-id"}'
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": "Method not found"},
            "id": "test-id",
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Request should raise JSONRPCError
        with pytest.raises(JSONRPCError) as exc_info:
            self.client._make_jsonrpc_request("invalid/method", {})

        assert "JSON-RPC error from SUT" in str(exc_info.value)
        assert exc_info.value.json_rpc_error == {"code": -32601, "message": "Method not found"}

    @patch("requests.Session.post")
    def test_send_message_interface(self, mock_post):
        """Test send_message method interface."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"jsonrpc": "2.0", "result": {"taskId": "task-123"}, "id": "req-1"}'
        mock_response.json.return_value = {"jsonrpc": "2.0", "result": {"taskId": "task-123"}, "id": "req-1"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Test message
        message = {"kind": "message", "messageId": "msg-123", "role": "user", "parts": [{"kind": "text", "text": "Hello"}]}

        result = self.client.send_message(message)

        # Verify correct method and params were used
        call_args = mock_post.call_args
        assert call_args[1]["json"]["method"] == "message/send"
        assert call_args[1]["json"]["params"] == {"message": message}

        # Verify result extraction
        assert result == {"taskId": "task-123"}

    @patch("requests.Session.post")
    def test_get_task_interface(self, mock_post):
        """Test get_task method interface."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"jsonrpc": "2.0", "result": {"taskId": "task-123", "status": "completed"}, "id": "req-1"}'
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": {"taskId": "task-123", "status": "completed"},
            "id": "req-1",
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.client.get_task("task-123", history_length=5)

        # Verify correct method and params were used
        call_args = mock_post.call_args
        assert call_args[1]["json"]["method"] == "tasks/get"
        assert call_args[1]["json"]["params"] == {"taskId": "task-123", "historyLength": 5}

        # Verify result extraction
        assert result == {"taskId": "task-123", "status": "completed"}

    @patch("requests.Session.post")
    def test_cancel_task_interface(self, mock_post):
        """Test cancel_task method interface."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"jsonrpc": "2.0", "result": {"taskId": "task-123", "status": "cancelled"}, "id": "req-1"}'
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": {"taskId": "task-123", "status": "cancelled"},
            "id": "req-1",
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.client.cancel_task("task-123")

        # Verify correct method and params were used
        call_args = mock_post.call_args
        assert call_args[1]["json"]["method"] == "tasks/cancel"
        assert call_args[1]["json"]["params"] == {"taskId": "task-123"}

        # Verify result extraction
        assert result == {"taskId": "task-123", "status": "cancelled"}

    def test_context_manager(self):
        """Test using client as context manager."""
        with JSONRPCClient("https://example.com/jsonrpc") as client:
            assert client.base_url == "https://example.com/jsonrpc"
            assert client.session is not None

        # Session should be closed after context exit
        # Note: In real usage, this would close the session

    def test_string_representations(self):
        """Test string representations."""
        str_repr = str(self.client)
        assert "JSONRPCClient" in str_repr
        assert "jsonrpc" in str_repr

        repr_str = repr(self.client)
        assert "JSONRPCClient" in repr_str
        assert "https://example.com/jsonrpc" in repr_str


@pytest.mark.core
class TestJSONRPCError:
    """Test cases for JSONRPCError."""

    def test_jsonrpc_error_creation(self):
        """Test JSONRPCError creation and properties."""
        json_error = {"code": -32601, "message": "Method not found"}
        original_error = ValueError("test error")

        error = JSONRPCError("Test error message", original_error=original_error, json_rpc_error=json_error)

        assert error.transport_type == TransportType.JSON_RPC
        assert error.original_error == original_error
        assert error.json_rpc_error == json_error
        assert "JSONRPC" in str(error)
        assert "Test error message" in str(error)
