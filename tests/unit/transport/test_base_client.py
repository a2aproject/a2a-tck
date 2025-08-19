"""
Unit tests for BaseTransportClient abstract class.

Tests the base transport client interface and common functionality
to ensure proper abstraction and error handling.

Specification Reference: A2A Protocol v0.3.0 §3.1 - Transport Layer Requirements
"""

import pytest
from abc import ABC
from typing import Any, Dict, Optional

from tck.transport.base_client import BaseTransportClient, TransportError, TransportType

# Import the core marker
pytestmark = pytest.mark.core


class MockTransportClient(BaseTransportClient):
    """Mock implementation of BaseTransportClient for testing."""

    def __init__(self, base_url: str, transport_type: TransportType):
        super().__init__(base_url, transport_type)
        self.method_calls = []

    def _record_call(self, method_name: str, **kwargs):
        """Helper to record method calls for testing."""
        self.method_calls.append({"method": method_name, "kwargs": kwargs})
        return {"mocked": True, "method": method_name}

    def send_message(self, message: Dict[str, Any], extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        return self._record_call("send_message", message=message, extra_headers=extra_headers)

    def send_streaming_message(self, message: Dict[str, Any], extra_headers: Optional[Dict[str, str]] = None) -> Any:
        return self._record_call("send_streaming_message", message=message, extra_headers=extra_headers)

    def get_task(
        self, task_id: str, history_length: Optional[int] = None, extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        return self._record_call("get_task", task_id=task_id, history_length=history_length, extra_headers=extra_headers)

    def cancel_task(self, task_id: str, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        return self._record_call("cancel_task", task_id=task_id, extra_headers=extra_headers)

    def resubscribe_task(self, task_id: str, extra_headers: Optional[Dict[str, str]] = None) -> Any:
        return self._record_call("resubscribe_task", task_id=task_id, extra_headers=extra_headers)

    def set_push_notification_config(
        self, task_id: str, config: Dict[str, Any], extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        return self._record_call("set_push_notification_config", task_id=task_id, config=config, extra_headers=extra_headers)

    def get_push_notification_config(
        self, task_id: str, config_id: str, extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        return self._record_call(
            "get_push_notification_config", task_id=task_id, config_id=config_id, extra_headers=extra_headers
        )

    def list_push_notification_configs(self, task_id: str, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        return self._record_call("list_push_notification_configs", task_id=task_id, extra_headers=extra_headers)

    def delete_push_notification_config(
        self, task_id: str, config_id: str, extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        return self._record_call(
            "delete_push_notification_config", task_id=task_id, config_id=config_id, extra_headers=extra_headers
        )

    def get_authenticated_extended_card(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        return self._record_call("get_authenticated_extended_card", extra_headers=extra_headers)


class TestTransportType:
    """Test TransportType enumeration."""

    def test_transport_type_values(self):
        """Test that TransportType has correct values."""
        assert TransportType.JSON_RPC.value == "jsonrpc"
        assert TransportType.GRPC.value == "grpc"
        assert TransportType.REST.value == "rest"

    def test_transport_type_count(self):
        """Test that we have exactly 3 transport types."""
        assert len(TransportType) == 3


class TestTransportError:
    """Test TransportError exception class."""

    def test_transport_error_basic(self):
        """Test basic TransportError creation."""
        error = TransportError("Test error", TransportType.JSON_RPC)
        assert str(error) == "[JSONRPC] Test error"
        assert error.transport_type == TransportType.JSON_RPC
        assert error.original_error is None

    def test_transport_error_with_original(self):
        """Test TransportError with original exception."""
        original = ValueError("Original error")
        error = TransportError("Test error", TransportType.GRPC, original)
        assert "[GRPC] Test error (caused by: Original error)" in str(error)
        assert error.original_error == original


class TestBaseTransportClient:
    """Test BaseTransportClient abstract class."""

    def test_abstract_class_cannot_instantiate(self):
        """Test that BaseTransportClient cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseTransportClient("http://example.com", TransportType.JSON_RPC)

    def test_mock_client_initialization(self):
        """Test mock client initialization."""
        client = MockTransportClient("http://example.com", TransportType.JSON_RPC)
        assert client.base_url == "http://example.com"
        assert client.transport_type == TransportType.JSON_RPC
        assert hasattr(client, "_logger")

    def test_supports_method_core_methods(self):
        """Test that all core methods are supported."""
        client = MockTransportClient("http://example.com", TransportType.JSON_RPC)

        core_methods = [
            "send_message",
            "send_streaming_message",
            "get_task",
            "cancel_task",
            "resubscribe_task",
            "set_push_notification_config",
            "get_push_notification_config",
            "list_push_notification_configs",
            "delete_push_notification_config",
            "get_authenticated_extended_card",
        ]

        for method in core_methods:
            assert client.supports_method(method), f"Core method {method} should be supported"

    def test_supports_method_list_tasks_transport_specific(self):
        """Test that list_tasks support depends on transport type."""
        jsonrpc_client = MockTransportClient("http://example.com", TransportType.JSON_RPC)
        grpc_client = MockTransportClient("http://example.com", TransportType.GRPC)
        rest_client = MockTransportClient("http://example.com", TransportType.REST)

        assert not jsonrpc_client.supports_method("list_tasks")
        assert grpc_client.supports_method("list_tasks")
        assert rest_client.supports_method("list_tasks")

    def test_supports_method_unknown_method(self):
        """Test that unknown methods are not supported."""
        client = MockTransportClient("http://example.com", TransportType.JSON_RPC)
        assert not client.supports_method("unknown_method")

    def test_list_tasks_not_implemented_for_jsonrpc(self):
        """Test that list_tasks raises NotImplementedError for JSON-RPC."""
        client = MockTransportClient("http://example.com", TransportType.JSON_RPC)

        with pytest.raises(NotImplementedError) as exc_info:
            client.list_tasks()
        assert "list_tasks is not supported by jsonrpc transport" in str(exc_info.value)

    def test_get_transport_info(self):
        """Test transport info generation."""
        client = MockTransportClient("http://example.com", TransportType.GRPC)
        info = client.get_transport_info()

        assert info["transport_type"] == "grpc"
        assert info["base_url"] == "http://example.com"
        assert "supported_methods" in info
        assert "send_message" in info["supported_methods"]
        assert "list_tasks" in info["supported_methods"]  # gRPC supports this

    def test_str_representation(self):
        """Test string representation of transport client."""
        client = MockTransportClient("http://example.com", TransportType.REST)
        str_repr = str(client)
        assert "MockTransportClient" in str_repr
        assert "rest" in str_repr
        assert "http://example.com" in str_repr

    def test_repr_representation(self):
        """Test repr representation of transport client."""
        client = MockTransportClient("http://example.com", TransportType.JSON_RPC)
        repr_str = repr(client)
        assert "MockTransportClient" in repr_str
        assert "base_url='http://example.com'" in repr_str
        assert "TransportType.JSON_RPC" in repr_str

    def test_method_call_recording(self):
        """Test that mock client records method calls properly."""
        client = MockTransportClient("http://example.com", TransportType.JSON_RPC)

        # Test a method call
        message = {"kind": "message", "messageId": "test", "role": "user", "parts": []}
        result = client.send_message(message, extra_headers={"Auth": "Bearer token"})

        assert result["mocked"] is True
        assert result["method"] == "send_message"
        assert len(client.method_calls) == 1
        assert client.method_calls[0]["method"] == "send_message"
        assert client.method_calls[0]["kwargs"]["message"] == message
        assert client.method_calls[0]["kwargs"]["extra_headers"] == {"Auth": "Bearer token"}

    def test_all_abstract_methods_implemented(self):
        """Test that mock client implements all abstract methods."""
        client = MockTransportClient("http://example.com", TransportType.JSON_RPC)

        # Verify no abstract methods remain unimplemented
        abstract_methods = BaseTransportClient.__abstractmethods__
        for method_name in abstract_methods:
            assert hasattr(client, method_name)
            assert callable(getattr(client, method_name))


if __name__ == "__main__":
    pytest.main([__file__])
