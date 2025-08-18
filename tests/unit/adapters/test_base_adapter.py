"""
Unit tests for BaseTransportAdapter

These tests verify the base adapter framework works correctly and provides
the foundation for transport-agnostic testing without mocking.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from typing import Dict, Any

from tests.adapters.base_adapter import BaseTransportAdapter, TestContext, TestResult, TestOutcome
from typing import Optional
from tck.transport.base_client import BaseTransportClient, TransportType, TransportError


class MockTransportClient(BaseTransportClient):
    """Mock transport client for testing adapter framework."""

    def __init__(self, base_url: str, transport_type: TransportType):
        super().__init__(base_url, transport_type)
        self.call_log = []

    def send_message(self, message: Dict[str, Any], **kwargs):
        self.call_log.append(("send_message", message, kwargs))
        return {"taskId": "test-task-123", "state": "pending", "createdAt": "2025-08-02T10:00:00Z"}

    def send_streaming_message(self, message: Dict[str, Any], **kwargs):
        self.call_log.append(("send_streaming_message", message, kwargs))
        return iter([{"taskId": "test-task-123", "state": "pending"}])

    def get_task(self, task_id: str, **kwargs):
        self.call_log.append(("get_task", task_id, kwargs))
        return {"taskId": task_id, "state": "completed", "createdAt": "2025-08-02T10:00:00Z"}

    def cancel_task(self, task_id: str, **kwargs):
        self.call_log.append(("cancel_task", task_id, kwargs))
        return {"taskId": task_id, "state": "cancelled"}

    def resubscribe_task(self, task_id: str, **kwargs):
        self.call_log.append(("resubscribe_task", task_id, kwargs))
        return iter([{"taskId": task_id, "state": "in-progress"}])

    def set_push_notification_config(self, task_id: str, config: Dict[str, Any], **kwargs):
        self.call_log.append(("set_push_notification_config", task_id, config, kwargs))
        return {"configId": "config-123"}

    def get_push_notification_config(self, task_id: str, config_id: str, **kwargs):
        self.call_log.append(("get_push_notification_config", task_id, config_id, kwargs))
        return {"configId": config_id, "endpoint": "https://example.com/webhook"}

    def list_push_notification_configs(self, task_id: str, **kwargs):
        self.call_log.append(("list_push_notification_configs", task_id, kwargs))
        return {"configs": []}

    def delete_push_notification_config(self, task_id: str, config_id: str, **kwargs):
        self.call_log.append(("delete_push_notification_config", task_id, config_id, kwargs))
        return {"success": True}

    def get_authenticated_extended_card(self, **kwargs):
        self.call_log.append(("get_authenticated_extended_card", kwargs))
        return {"name": "Test Agent", "protocol_version": "0.3.0", "endpoint": "https://example.com/jsonrpc"}


class TestTransportAdapter(BaseTransportAdapter):
    """Concrete test adapter implementation."""

    def test_send_message(self, context: TestContext, message: Dict[str, Any]) -> TestResult:
        try:

            def test_func():
                return self.transport_client.send_message(message, extra_headers=context.extra_headers)

            result, duration = self.execute_test_with_timing(test_func, context)

            # Validate response
            failures = self.assert_valid_task_response(result, context)

            return self.create_test_result(
                TestOutcome.PASS if not failures else TestOutcome.FAIL,
                context,
                duration_ms=duration,
                sut_response=result,
                error_message="; ".join(failures) if failures else None,
                assertions_passed=len(failures) == 0,
                assertions_total=1,
            )
        except Exception as e:
            return self.create_test_result(TestOutcome.ERROR, context, error_message=str(e))

    def test_send_streaming_message(self, context: TestContext, message: Dict[str, Any]) -> TestResult:
        try:

            def test_func():
                stream = self.transport_client.send_streaming_message(message, extra_headers=context.extra_headers)
                return list(stream)  # Consume the stream for testing

            result, duration = self.execute_test_with_timing(test_func, context)

            return self.create_test_result(
                TestOutcome.PASS,
                context,
                duration_ms=duration,
                sut_response={"stream_items": len(result)},
                assertions_passed=1,
                assertions_total=1,
            )
        except Exception as e:
            return self.create_test_result(TestOutcome.ERROR, context, error_message=str(e))

    def test_get_task(self, context: TestContext, task_id: str, history_length: Optional[int] = None) -> TestResult:
        try:

            def test_func():
                return self.transport_client.get_task(task_id, history_length=history_length, extra_headers=context.extra_headers)

            result, duration = self.execute_test_with_timing(test_func, context)

            # Validate response
            failures = self.assert_valid_task_response(result, context)

            return self.create_test_result(
                TestOutcome.PASS if not failures else TestOutcome.FAIL,
                context,
                duration_ms=duration,
                sut_response=result,
                error_message="; ".join(failures) if failures else None,
                assertions_passed=len(failures) == 0,
                assertions_total=1,
            )
        except Exception as e:
            return self.create_test_result(TestOutcome.ERROR, context, error_message=str(e))

    def test_cancel_task(self, context: TestContext, task_id: str) -> TestResult:
        try:

            def test_func():
                return self.transport_client.cancel_task(task_id, extra_headers=context.extra_headers)

            result, duration = self.execute_test_with_timing(test_func, context)

            return self.create_test_result(
                TestOutcome.PASS, context, duration_ms=duration, sut_response=result, assertions_passed=1, assertions_total=1
            )
        except Exception as e:
            return self.create_test_result(TestOutcome.ERROR, context, error_message=str(e))

    def test_get_agent_card(self, context: TestContext) -> TestResult:
        try:

            def test_func():
                return self.transport_client.get_authenticated_extended_card(extra_headers=context.extra_headers)

            result, duration = self.execute_test_with_timing(test_func, context)

            # Validate response
            failures = self.assert_valid_agent_card(result, context)

            return self.create_test_result(
                TestOutcome.PASS if not failures else TestOutcome.FAIL,
                context,
                duration_ms=duration,
                sut_response=result,
                error_message="; ".join(failures) if failures else None,
                assertions_passed=len(failures) == 0,
                assertions_total=1,
            )
        except Exception as e:
            return self.create_test_result(TestOutcome.ERROR, context, error_message=str(e))


@pytest.mark.core
class TestTestContext:
    """Test TestContext dataclass."""

    def test_basic_creation(self):
        """Test basic TestContext creation."""
        context = TestContext(
            transport_type=TransportType.JSON_RPC, sut_endpoint="https://example.com/jsonrpc", test_name="test_basic_message"
        )

        assert context.transport_type == TransportType.JSON_RPC
        assert context.sut_endpoint == "https://example.com/jsonrpc"
        assert context.test_name == "test_basic_message"
        assert context.spec_reference is None
        assert context.extra_headers == {}
        assert context.timeout == 30.0
        assert "start_time" in context.metadata
        assert isinstance(context.metadata["start_time"], datetime)

    def test_with_optional_fields(self):
        """Test TestContext with optional fields."""
        headers = {"Authorization": "Bearer test-token"}
        context = TestContext(
            transport_type=TransportType.GRPC,
            sut_endpoint="grpc://example.com:50051",
            test_name="test_authenticated_message",
            spec_reference="A2A v0.3.0 §7.1",
            extra_headers=headers,
            timeout=60.0,
        )

        assert context.spec_reference == "A2A v0.3.0 §7.1"
        assert context.extra_headers == headers
        assert context.timeout == 60.0


@pytest.mark.core
class TestTestResult:
    """Test TestResult dataclass."""

    def test_basic_creation(self):
        """Test basic TestResult creation."""
        result = TestResult(outcome=TestOutcome.PASS, test_name="test_message_send", transport_type=TransportType.REST)

        assert result.outcome == TestOutcome.PASS
        assert result.test_name == "test_message_send"
        assert result.transport_type == TransportType.REST
        assert result.success_rate == 1.0

    def test_with_assertions(self):
        """Test TestResult with assertion counts."""
        result = TestResult(
            outcome=TestOutcome.PASS,
            test_name="test_task_validation",
            transport_type=TransportType.JSON_RPC,
            assertions_passed=8,
            assertions_total=10,
        )

        assert result.success_rate == 0.8

    def test_string_representation(self):
        """Test TestResult string representation."""
        result = TestResult(
            outcome=TestOutcome.PASS,
            test_name="test_basic",
            transport_type=TransportType.GRPC,
            duration_ms=150.5,
            assertions_passed=5,
            assertions_total=5,
        )

        str_repr = str(result)
        assert "test_basic" in str_repr
        assert "grpc" in str_repr
        assert "PASS" in str_repr
        assert "150.5ms" in str_repr
        assert "5/5" in str_repr


@pytest.mark.core
class TestBaseTransportAdapter:
    """Test BaseTransportAdapter functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create mock transport client."""
        return MockTransportClient("https://example.com/jsonrpc", TransportType.JSON_RPC)

    @pytest.fixture
    def adapter(self, mock_client):
        """Create test adapter instance."""
        return TestTransportAdapter(mock_client)

    @pytest.fixture
    def test_context(self):
        """Create test context."""
        return TestContext(
            transport_type=TransportType.JSON_RPC,
            sut_endpoint="https://example.com/jsonrpc",
            test_name="test_adapter_functionality",
            spec_reference="A2A v0.3.0 §7.1",
        )

    def test_adapter_initialization(self, mock_client):
        """Test adapter initialization."""
        adapter = TestTransportAdapter(mock_client)

        assert adapter.transport_client is mock_client
        assert adapter.transport_type == TransportType.JSON_RPC
        assert adapter.sut_endpoint == "https://example.com/jsonrpc"

    def test_send_message_test(self, adapter, test_context):
        """Test send_message test execution."""
        message = {"content": "Hello, A2A!", "type": "text"}

        result = adapter.test_send_message(test_context, message)

        assert result.outcome == TestOutcome.PASS
        assert result.test_name == "test_adapter_functionality"
        assert result.transport_type == TransportType.JSON_RPC
        assert result.duration_ms is not None
        assert result.duration_ms > 0
        assert result.sut_response is not None
        assert result.assertions_passed == 1
        assert result.assertions_total == 1

        # Verify the mock client was called
        assert len(adapter.transport_client.call_log) == 1
        call = adapter.transport_client.call_log[0]
        assert call[0] == "send_message"
        assert call[1] == message

    def test_get_task_test(self, adapter, test_context):
        """Test get_task test execution."""
        task_id = "test-task-456"

        result = adapter.test_get_task(test_context, task_id, history_length=5)

        assert result.outcome == TestOutcome.PASS
        assert result.sut_response["taskId"] == task_id
        assert result.duration_ms is not None

        # Verify the mock client was called
        call = adapter.transport_client.call_log[0]
        assert call[0] == "get_task"
        assert call[1] == task_id
        assert call[2]["history_length"] == 5

    def test_streaming_message_test(self, adapter, test_context):
        """Test streaming message test execution."""
        message = {"content": "Streaming message", "type": "text"}

        result = adapter.test_send_streaming_message(test_context, message)

        assert result.outcome == TestOutcome.PASS
        assert result.sut_response["stream_items"] == 1
        assert result.duration_ms is not None

    def test_assert_valid_task_response(self, adapter, test_context):
        """Test task response validation."""
        # Valid response
        valid_response = {"taskId": "task-123", "state": "completed", "createdAt": "2025-08-02T10:00:00Z"}
        failures = adapter.assert_valid_task_response(valid_response, test_context)
        assert len(failures) == 0

        # Invalid response - missing required field
        invalid_response = {
            "taskId": "task-123",
            "createdAt": "2025-08-02T10:00:00Z",
            # Missing 'state'
        }
        failures = adapter.assert_valid_task_response(invalid_response, test_context)
        assert len(failures) == 1
        assert "Missing required field 'state'" in failures[0]

        # Invalid state
        invalid_state_response = {"taskId": "task-123", "state": "invalid-state", "createdAt": "2025-08-02T10:00:00Z"}
        failures = adapter.assert_valid_task_response(invalid_state_response, test_context)
        assert len(failures) == 1
        assert "Invalid task state 'invalid-state'" in failures[0]

    def test_assert_valid_agent_card(self, adapter, test_context):
        """Test agent card validation."""
        # Valid agent card
        valid_card = {"protocol_version": "0.3.0", "name": "Test Agent", "endpoint": "https://example.com/jsonrpc"}
        failures = adapter.assert_valid_agent_card(valid_card, test_context)
        assert len(failures) == 0

        # Invalid version
        invalid_version_card = {"protocol_version": "0.2.5", "name": "Test Agent", "endpoint": "https://example.com/jsonrpc"}
        failures = adapter.assert_valid_agent_card(invalid_version_card, test_context)
        assert len(failures) == 1
        assert "Expected A2A v0.3.x protocol version" in failures[0]

    def test_transport_error_handling(self, adapter, test_context):
        """Test transport error assertion."""
        # Valid transport error
        valid_error = TransportError("Connection failed", TransportType.JSON_RPC)
        failures = adapter.assert_transport_error_handling(valid_error, test_context)
        assert len(failures) == 0

        # Wrong transport type
        wrong_transport_error = TransportError("Connection failed", TransportType.GRPC)
        failures = adapter.assert_transport_error_handling(wrong_transport_error, test_context)
        assert len(failures) == 1
        assert "transport type" in failures[0]

        # Not a transport error
        generic_error = ValueError("Generic error")
        failures = adapter.assert_transport_error_handling(generic_error, test_context)
        assert len(failures) == 1
        assert "Expected TransportError" in failures[0]

    def test_execute_test_with_timing(self, adapter, test_context):
        """Test timing functionality."""

        def slow_test():
            import time

            time.sleep(0.01)  # 10ms sleep
            return "test result"

        result, duration = adapter.execute_test_with_timing(slow_test, test_context)

        assert result == "test result"
        assert duration >= 10.0  # At least 10ms
        assert duration < 100.0  # But not too long

    def test_capability_methods(self, adapter):
        """Test transport capability detection."""
        assert adapter.supports_streaming() is True
        assert adapter.supports_bidirectional_streaming() is False  # Base implementation
        assert adapter.supports_method("send_message") is True

    def test_compliance_test_suite(self, adapter, test_context):
        """Test running a compliance test suite."""
        test_scenarios = [
            {
                "name": "basic_message",
                "type": "send_message",
                "message": {"content": "Test message", "type": "text"},
                "spec_reference": "A2A v0.3.0 §7.1",
            },
            {"name": "task_retrieval", "type": "get_task", "task_id": "test-task-789"},
        ]

        results = adapter.run_compliance_test_suite(test_scenarios, test_context)

        assert len(results) == 2
        assert all(r.outcome == TestOutcome.PASS for r in results)
        assert results[0].test_name.endswith("::basic_message")
        assert results[1].test_name.endswith("::task_retrieval")

    def test_get_transport_info(self, adapter):
        """Test transport info retrieval."""
        info = adapter.get_transport_info()

        assert info["adapter_class"] == "TestTransportAdapter"
        assert info["transport_type"] == "jsonrpc"
        assert info["sut_endpoint"] == "https://example.com/jsonrpc"
        assert "supported_methods" in info
        assert "send_message" in info["supported_methods"]

    def test_string_representations(self, adapter):
        """Test string representations."""
        str_repr = str(adapter)
        assert "TestTransportAdapter" in str_repr
        assert "jsonrpc" in str_repr

        repr_str = repr(adapter)
        assert "TestTransportAdapter" in repr_str
        assert "transport_type=<TransportType.JSON_RPC: 'jsonrpc'>" in repr_str
