"""
Unit tests for JSONRPCTestAdapter

These tests verify the JSON-RPC specific adapter functionality and ensure
it properly integrates with the base adapter framework for real SUT testing.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any

from tests.adapters.jsonrpc_adapter import JSONRPCTestAdapter
from tests.adapters.base_adapter import TestContext, TestResult, TestOutcome
from tck.transport.jsonrpc_client import JSONRPCClient, JSONRPCError
from tck.transport.base_client import TransportType, TransportError


class MockJSONRPCClient(JSONRPCClient):
    """Mock JSON-RPC client for testing adapter functionality."""

    def __init__(self, base_url: str = "https://example.com/jsonrpc"):
        # Initialize without calling parent __init__ to avoid session creation
        self.base_url = base_url
        self.transport_type = TransportType.JSON_RPC
        self.call_log = []
        self.timeout = 30.0
        self.max_retries = 3

        # Mock session
        self.session = Mock()

    def _make_jsonrpc_request(self, method: str, params=None, request_id=None, extra_headers=None):
        self.call_log.append(("_make_jsonrpc_request", method, params, request_id, extra_headers))

        # Return appropriate mock responses based on method
        if method == "message/send":
            return {
                "jsonrpc": "2.0",
                "result": {"taskId": "test-task-123", "state": "pending", "createdAt": "2025-08-02T10:00:00Z"},
                "id": request_id or "test-id",
            }
        elif method == "tasks/get":
            task_id = params.get("taskId", "unknown-task")
            return {
                "jsonrpc": "2.0",
                "result": {
                    "taskId": task_id,
                    "state": "completed",
                    "createdAt": "2025-08-02T10:00:00Z",
                    "completedAt": "2025-08-02T10:05:00Z",
                },
                "id": request_id or "test-id",
            }
        elif method == "tasks/cancel":
            task_id = params.get("taskId", "unknown-task")
            return {"jsonrpc": "2.0", "result": {"taskId": task_id, "state": "cancelled"}, "id": request_id or "test-id"}
        elif method == "agent/getAuthenticatedExtendedCard":
            return {
                "jsonrpc": "2.0",
                "result": {"protocol_version": "0.3.0", "name": "Test JSON-RPC Agent", "endpoint": "https://example.com/jsonrpc"},
                "id": request_id or "test-id",
            }
        else:
            return {"jsonrpc": "2.0", "result": {"success": True}, "id": request_id or "test-id"}

    def send_message(self, message: Dict[str, Any], extra_headers=None):
        self.call_log.append(("send_message", message, extra_headers))
        response = self._make_jsonrpc_request("message/send", {"message": message}, extra_headers=extra_headers)
        return response["result"]

    def send_streaming_message(self, message: Dict[str, Any], extra_headers=None):
        self.call_log.append(("send_streaming_message", message, extra_headers))
        # For streaming, return proper task data
        yield {"taskId": "test-task-stream-123", "state": "pending", "createdAt": "2025-08-02T10:00:00Z"}

    def get_task(self, task_id: str, history_length=None, extra_headers=None):
        self.call_log.append(("get_task", task_id, history_length, extra_headers))
        params = {"taskId": task_id}
        if history_length is not None:
            params["historyLength"] = history_length
        response = self._make_jsonrpc_request("tasks/get", params, extra_headers=extra_headers)
        return response["result"]

    def cancel_task(self, task_id: str, extra_headers=None):
        self.call_log.append(("cancel_task", task_id, extra_headers))
        response = self._make_jsonrpc_request("tasks/cancel", {"taskId": task_id}, extra_headers=extra_headers)
        return response["result"]

    def get_agent_card(self, extra_headers=None):
        self.call_log.append(("get_agent_card", extra_headers))
        response = self._make_jsonrpc_request("agent/getAuthenticatedExtendedCard", {}, extra_headers=extra_headers)
        return response["result"]

    # Implement remaining abstract methods with minimal functionality
    def resubscribe_task(self, task_id: str, extra_headers=None):
        return iter([{"taskId": task_id, "state": "in-progress"}])

    def set_push_notification_config(self, task_id: str, config: Dict[str, Any], extra_headers=None):
        return {"configId": "config-123"}

    def get_push_notification_config(self, task_id: str, config_id: str, extra_headers=None):
        return {"configId": config_id, "endpoint": "https://example.com/webhook"}

    def list_push_notification_configs(self, task_id: str, extra_headers=None):
        return {"configs": []}

    def delete_push_notification_config(self, task_id: str, config_id: str, extra_headers=None):
        return {"success": True}

    def get_authenticated_extended_card(self, extra_headers=None):
        return {"name": "Test Agent", "protocol_version": "0.3.0", "endpoint": self.base_url}


@pytest.mark.core
class TestJSONRPCTestAdapter:
    """Test JSON-RPC specific adapter functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create mock JSON-RPC client."""
        return MockJSONRPCClient()

    @pytest.fixture
    def adapter(self, mock_client):
        """Create JSON-RPC adapter instance."""
        return JSONRPCTestAdapter(mock_client)

    @pytest.fixture
    def test_context(self):
        """Create test context for JSON-RPC."""
        return TestContext(
            transport_type=TransportType.JSON_RPC,
            sut_endpoint="https://example.com/jsonrpc",
            test_name="test_jsonrpc_functionality",
            spec_reference="A2A v0.3.0 §3.2.1",
        )

    def test_adapter_initialization(self, mock_client):
        """Test JSON-RPC adapter initialization."""
        adapter = JSONRPCTestAdapter(mock_client)

        assert adapter.transport_client is mock_client
        assert adapter.jsonrpc_client is mock_client
        assert adapter.transport_type == TransportType.JSON_RPC
        assert adapter.sut_endpoint == "https://example.com/jsonrpc"

    def test_initialization_with_wrong_client_type(self):
        """Test adapter initialization with wrong client type."""
        wrong_client = Mock()
        wrong_client.transport_type = TransportType.GRPC

        with pytest.raises(ValueError, match="Expected JSONRPCClient"):
            JSONRPCTestAdapter(wrong_client)

    def test_send_message_success(self, adapter, test_context):
        """Test successful message sending."""
        adapter.jsonrpc_client.call_log.clear()  # Clear previous calls
        message = {"content": "Test message", "type": "text"}

        result = adapter.test_send_message(test_context, message)

        assert result.outcome == TestOutcome.PASS
        assert result.test_name == "test_jsonrpc_functionality"
        assert result.transport_type == TransportType.JSON_RPC
        assert result.duration_ms is not None
        assert result.sut_response is not None
        assert result.sut_response["taskId"] == "test-task-123"
        assert result.assertions_passed == 1
        assert result.assertions_total == 1

        # Verify the mock client was called (both send_message and _make_jsonrpc_request)
        assert len(adapter.jsonrpc_client.call_log) >= 1
        # Find the send_message call
        send_message_calls = [call for call in adapter.jsonrpc_client.call_log if call[0] == "send_message"]
        assert len(send_message_calls) == 1
        call = send_message_calls[0]
        assert call[1] == message

    def test_send_message_with_jsonrpc_error(self, adapter, test_context):
        """Test message sending with JSON-RPC error."""
        # Mock the client to raise JSONRPCError
        adapter.jsonrpc_client.send_message = Mock(side_effect=JSONRPCError("Connection failed"))

        message = {"content": "Test message", "type": "text"}
        result = adapter.test_send_message(test_context, message)

        assert result.outcome == TestOutcome.ERROR
        assert "JSON-RPC error" in result.error_message
        assert result.assertions_passed == 0

    def test_send_streaming_message_success(self, adapter, test_context):
        """Test successful streaming message."""
        message = {"content": "Streaming test", "type": "text"}

        result = adapter.test_send_streaming_message(test_context, message)

        assert result.outcome == TestOutcome.PASS
        assert result.sut_response["stream_items"] == 1
        assert result.sut_response["first_item"]["taskId"] == "test-task-stream-123"
        assert result.duration_ms is not None

    def test_get_task_success(self, adapter, test_context):
        """Test successful task retrieval."""
        adapter.jsonrpc_client.call_log.clear()  # Clear previous calls
        task_id = "test-task-456"

        result = adapter.test_get_task(test_context, task_id, history_length=5)

        assert result.outcome == TestOutcome.PASS
        assert result.sut_response["taskId"] == task_id
        assert result.duration_ms is not None

        # Verify the mock client was called correctly
        get_task_calls = [call for call in adapter.jsonrpc_client.call_log if call[0] == "get_task"]
        assert len(get_task_calls) == 1
        call = get_task_calls[0]
        assert call[1] == task_id
        assert call[2] == 5  # history_length

    def test_get_task_with_wrong_task_id(self, adapter, test_context):
        """Test task retrieval that returns wrong task ID."""
        # Mock to return different task ID than requested
        adapter.jsonrpc_client.get_task = Mock(
            return_value={"taskId": "different-task", "state": "completed", "createdAt": "2025-08-02T10:00:00Z"}
        )

        result = adapter.test_get_task(test_context, "requested-task")

        assert result.outcome == TestOutcome.FAIL
        assert "doesn't match requested" in result.error_message

    def test_cancel_task_success(self, adapter, test_context):
        """Test successful task cancellation."""
        task_id = "test-task-789"

        result = adapter.test_cancel_task(test_context, task_id)

        assert result.outcome == TestOutcome.PASS
        assert result.sut_response["taskId"] == task_id
        assert result.duration_ms is not None

    def test_get_agent_card_success(self, adapter, test_context):
        """Test successful agent card retrieval."""
        result = adapter.test_get_agent_card(test_context)

        assert result.outcome == TestOutcome.PASS
        assert result.sut_response["protocol_version"] == "0.3.0"
        assert result.sut_response["name"] == "Test JSON-RPC Agent"
        assert result.duration_ms is not None

    def test_raw_json_rpc_call(self, adapter, test_context):
        """Test raw JSON-RPC method call."""
        result = adapter.test_raw_json_rpc_call(test_context, "custom/method", {"param1": "value1"})

        assert result.outcome == TestOutcome.PASS
        assert result.sut_response["result"]["success"] is True
        assert result.duration_ms is not None

        # Verify the call was made
        call = adapter.jsonrpc_client.call_log[0]
        assert call[0] == "_make_jsonrpc_request"
        assert call[1] == "custom/method"
        assert call[2] == {"param1": "value1"}

    def test_jsonrpc_task_response_validation(self, adapter, test_context):
        """Test JSON-RPC specific task response validation."""
        # Valid response
        valid_response = {"taskId": "test-123", "state": "completed", "createdAt": "2025-08-02T10:00:00Z"}
        failures = adapter._assert_valid_jsonrpc_task_response(valid_response, test_context)
        assert len(failures) == 0

        # Invalid timestamp format
        invalid_timestamp_response = {"taskId": "test-123", "state": "completed", "createdAt": "invalid-timestamp"}
        failures = adapter._assert_valid_jsonrpc_task_response(invalid_timestamp_response, test_context)
        assert len(failures) == 1
        assert "Invalid timestamp format" in failures[0]

        # Non-string task ID
        invalid_taskid_response = {
            "taskId": 123,  # Should be string
            "state": "completed",
            "createdAt": "2025-08-02T10:00:00Z",
        }
        failures = adapter._assert_valid_jsonrpc_task_response(invalid_taskid_response, test_context)
        assert len(failures) == 1
        assert "taskId must be string" in failures[0]

    def test_capability_methods(self, adapter):
        """Test JSON-RPC specific capability detection."""
        assert adapter.supports_streaming() is True
        assert adapter.supports_bidirectional_streaming() is False
        assert adapter.supports_method("send_message") is True
        assert adapter.supports_method("list_tasks") is False  # Not supported in JSON-RPC

    def test_get_transport_info(self, adapter):
        """Test JSON-RPC transport info retrieval."""
        info = adapter.get_transport_info()

        assert info["adapter_class"] == "JSONRPCTestAdapter"
        assert info["transport_type"] == "jsonrpc"
        assert info["json_rpc_version"] == "2.0"
        assert info["supports_server_sent_events"] is True
        assert info["supports_bidirectional_streaming"] is False
        assert info["legacy_compatibility"] is True
        assert info["request_timeout"] == 30.0
        assert info["max_retries"] == 3

    def test_create_compliance_test_scenarios(self, adapter):
        """Test creation of JSON-RPC compliance test scenarios."""
        scenarios = adapter.create_compliance_test_scenarios()

        assert len(scenarios) == 3

        # Verify basic message scenario
        message_scenario = scenarios[0]
        assert message_scenario["name"] == "basic_message_send"
        assert message_scenario["type"] == "send_message"
        assert message_scenario["spec_reference"] == "A2A v0.3.0 §7.1"

        # Verify streaming scenario
        streaming_scenario = scenarios[1]
        assert streaming_scenario["name"] == "streaming_message"
        assert streaming_scenario["type"] == "send_streaming_message"

        # Verify agent card scenario
        card_scenario = scenarios[2]
        assert card_scenario["name"] == "agent_card_retrieval"
        assert card_scenario["type"] == "get_agent_card"

    def test_run_compliance_test_suite(self, adapter, test_context):
        """Test running JSON-RPC compliance test suite."""
        scenarios = adapter.create_compliance_test_scenarios()
        results = adapter.run_compliance_test_suite(scenarios, test_context)

        assert len(results) == 3
        assert all(r.outcome == TestOutcome.PASS for r in results)

        # Verify test names
        test_names = [r.test_name for r in results]
        assert any("basic_message_send" in name for name in test_names)
        assert any("streaming_message" in name for name in test_names)
        assert any("agent_card_retrieval" in name for name in test_names)

    def test_error_handling_with_transport_error(self, adapter, test_context):
        """Test error handling with TransportError."""
        # Mock to raise TransportError instead of JSONRPCError
        adapter.jsonrpc_client.send_message = Mock(side_effect=TransportError("Network error", TransportType.JSON_RPC))

        message = {"content": "Test message", "type": "text"}
        result = adapter.test_send_message(test_context, message)

        assert result.outcome == TestOutcome.ERROR
        assert "Unexpected error" in result.error_message

    def test_string_representations(self, adapter):
        """Test string representations."""
        str_repr = str(adapter)
        assert "JSONRPCTestAdapter" in str_repr
        assert "jsonrpc" in str_repr

        repr_str = repr(adapter)
        assert "JSONRPCTestAdapter" in repr_str


@pytest.mark.core
def test_jsonrpc_adapter_integration():
    """Integration test for JSON-RPC adapter."""
    # Test that adapter integrates properly with real JSONRPCClient interface
    from tck.transport.jsonrpc_client import JSONRPCClient

    # Create a real JSONRPCClient (but don't make actual network calls)
    with patch("tck.transport.jsonrpc_client.requests.Session"):
        client = JSONRPCClient("https://example.com/jsonrpc")
        adapter = JSONRPCTestAdapter(client)

        assert adapter.transport_type == TransportType.JSON_RPC
        assert adapter.jsonrpc_client is client
        assert isinstance(adapter.get_transport_info(), dict)

        # Test capability detection
        assert not adapter.supports_method("list_tasks")
        assert adapter.supports_method("send_message")

        print("✓ JSON-RPC adapter integrates correctly with real JSONRPCClient")
