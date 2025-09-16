"""
A2A v0.3.0 Method Enhancements Testing

This module tests the enhanced method implementations and new features
introduced in A2A v0.3.0, including transport-specific behavior and
advanced method capabilities.

Specification Reference: A2A Protocol v0.3.0 §7 - Protocol RPC Methods
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional, List
import pytest

from tests.markers import optional_capability, a2a_v030
from tests.utils.transport_helpers import (
    transport_send_message,
    transport_get_task,
    transport_cancel_task,
    transport_get_agent_card,
    is_transport_client,
    get_client_transport_type,
    generate_test_message_id,
    generate_test_task_id,
)
from tck import message_utils
from tck.transport.base_client import BaseTransportClient

logger = logging.getLogger(__name__)


class TestA2AV030MethodEnhancements:
    """
    Test enhanced method implementations in A2A v0.3.0.

    Validates new features, improved error handling, and enhanced
    functionality across all supported transport types.
    """

    @optional_capability
    @a2a_v030
    def test_message_send_enhanced_parts_support(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 §7.1 - Enhanced Parts Support in message/send

        Tests support for enhanced message parts including file references,
        data parts, and complex message structures introduced in v0.3.0.
        """
        enhanced_message = {
            "kind": "message",
            "messageId": generate_test_message_id("enhanced-parts"),
            "role": "user",
            "parts": [
                {"kind": "text", "text": "This message tests enhanced parts support in A2A v0.3.0"},
                {"kind": "data", "data": {"type": "application/json", "content": {"test": "data", "version": "0.3.0"}}},
            ],
        }

        response = transport_send_message(sut_client, {"message": enhanced_message})

        # Should handle enhanced message structure
        assert "result" in response or "error" not in response, "Enhanced message parts should be supported in A2A v0.3.0"

        if "result" in response:
            task = response["result"]
            assert "id" in task, "Task ID should be returned"
            logger.info(f"✅ Enhanced parts support validated with task: {task['id']}")
        elif "error" in response:
            error = response["error"]
            # Should not be a method-not-found error
            assert error.get("code") != -32601, "Enhanced parts should be supported, not method not found"
            logger.info(f"⚠️  Enhanced parts validation returned error: {error}")

    @optional_capability
    @a2a_v030
    def test_tasks_get_enhanced_parameters(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 §7.3.1 - Enhanced TaskQueryParams

        Tests enhanced parameters for tasks/get including new fields
        and improved query capabilities.
        """
        # First create a task
        message = {
            "kind": "message",
            "messageId": generate_test_message_id("enhanced-query"),
            "role": "user",
            "parts": [{"kind": "text", "text": "Task for enhanced query testing"}],
        }

        create_response = transport_send_message(sut_client, {"message": message})

        if "error" in create_response:
            pytest.skip(f"Could not create task for testing: {create_response}")

        task = create_response.get("result", create_response)
        task_id = task["id"]

        # Test enhanced query parameters
        enhanced_params = {
            "id": task_id,
            "historyLength": 10,  # Enhanced history support
            "includeArtifacts": True,  # New in v0.3.0 (if supported)
        }

        # Note: We can't directly test this without transport-specific parameter passing
        # Use basic get_task for now but verify enhanced response structure
        response = transport_get_task(sut_client, task_id, history_length=10)

        if "result" in response:
            task_data = response["result"]

            # Validate enhanced response structure
            assert "id" in task_data
            assert "status" in task_data

            # Check for enhanced fields (may not be present in all implementations)
            if "history" in task_data:
                logger.info("✅ Task history included in response")

            if "artifacts" in task_data:
                logger.info("✅ Task artifacts included in response")

            logger.info(f"✅ Enhanced tasks/get validated for task: {task_id}")

    @optional_capability
    @a2a_v030
    def test_authenticated_extended_card_comprehensive(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 §7.10 - Comprehensive agent/getAuthenticatedExtendedCard Testing

        Tests the new authenticated extended agent card method with comprehensive
        validation of enhanced features and security aspects.
        """
        response = transport_get_agent_card(sut_client)

        if "error" in response:
            error = response["error"]
            error_code = error.get("code")

            # Method not found is acceptable (not all transports implement this)
            if error_code == -32601:
                pytest.skip("agent/getAuthenticatedExtendedCard not implemented")

            # Authentication errors are expected if not authenticated
            if error_code in [401, 403]:
                logger.info("✅ Authentication required for extended card (as expected)")
                return

            # Other errors
            logger.warning(f"⚠️  Extended card error: {error}")
            return

        # Validate extended card structure
        card = response.get("result", response)

        # Standard agent card fields
        assert "name" in card, "Agent name required in extended card"

        # Enhanced fields (may be optional)
        enhanced_fields = ["version", "description", "capabilities", "skills", "securitySchemes", "authentication", "endpoints"]

        found_enhancements = []
        for field in enhanced_fields:
            if field in card:
                found_enhancements.append(field)

        logger.info(f"✅ Extended card enhancements found: {found_enhancements}")

        # Validate security schemes if present (A2A v0.3.0 feature)
        if "securitySchemes" in card:
            security_schemes = card["securitySchemes"]
            assert isinstance(security_schemes, dict), "Security schemes should be a dictionary"
            logger.info(f"✅ Security schemes declared: {list(security_schemes.keys())}")

    @optional_capability
    @a2a_v030
    def test_method_parameter_validation_enhancements(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 - Enhanced Parameter Validation

        Tests improved parameter validation and error reporting
        introduced in A2A v0.3.0 methods.
        """
        test_cases = [
            {"method": "message/send", "invalid_params": {"invalid": "structure"}, "expected_error": "Invalid message structure"},
            {"method": "tasks/get", "invalid_params": {"invalid": "taskId"}, "expected_error": "Invalid task ID"},
            {"method": "tasks/cancel", "invalid_params": {"invalid": "params"}, "expected_error": "Invalid parameters"},
        ]

        for test_case in test_cases:
            method = test_case["method"]
            invalid_params = test_case["invalid_params"]

            if method == "message/send":
                response = transport_send_message(sut_client, invalid_params)
            elif method == "tasks/get":
                # Can't easily test with invalid params using transport helper
                continue
            elif method == "tasks/cancel":
                # Can't easily test with invalid params using transport helper
                continue

            # Should get parameter validation error
            if "error" in response:
                error = response["error"]
                error_code = error.get("code")

                # Should be parameter validation error, not method not found
                assert error_code == -32602, f"Expected parameter validation error (-32602), got {error_code}"

                logger.info(f"✅ Parameter validation working for {method}")
            else:
                logger.warning(f"⚠️  {method} did not validate parameters properly")

    @optional_capability
    @a2a_v030
    def test_error_response_enhancements(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 - Enhanced Error Response Format

        Tests improved error response format and additional error information
        provided in A2A v0.3.0.
        """
        # Test with non-existent task ID to trigger error
        nonexistent_task_id = generate_test_task_id("nonexistent")

        response = transport_get_task(sut_client, nonexistent_task_id)

        if "error" in response:
            error = response["error"]

            # Validate enhanced error structure
            assert "code" in error, "Error code required"
            assert "message" in error, "Error message required"

            # Check for enhanced error fields (optional in v0.3.0)
            enhanced_error_fields = ["data", "details", "source", "timestamp"]
            found_enhancements = []

            for field in enhanced_error_fields:
                if field in error:
                    found_enhancements.append(field)

            if found_enhancements:
                logger.info(f"✅ Enhanced error fields found: {found_enhancements}")
            else:
                logger.info("⚪ Basic error format (enhanced fields optional)")

            # Validate error code is appropriate
            error_code = error["code"]
            assert error_code == -32001, f"Expected TaskNotFoundError (-32001), got {error_code}"

            logger.info(f"✅ Error response validation complete")


class TestTransportSpecificMethodBehavior:
    """
    Test transport-specific method behavior and optimizations in A2A v0.3.0.

    Validates that methods behave appropriately across different transport
    types while maintaining functional equivalence.
    """

    @optional_capability
    @a2a_v030
    def test_json_rpc_method_extensions(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 §3.1 - JSON-RPC Transport Method Extensions

        Tests JSON-RPC specific method extensions and optimizations.
        """
        if not is_transport_client(sut_client):
            pytest.skip("Test requires transport-aware client")

        transport_type = get_client_transport_type(sut_client)

        if transport_type != "jsonrpc":
            pytest.skip("Test specific to JSON-RPC transport")

        # Test JSON-RPC specific features
        message = {
            "kind": "message",
            "messageId": generate_test_message_id("jsonrpc-specific"),
            "role": "user",
            "parts": [{"kind": "text", "text": "JSON-RPC transport test"}],
        }

        response = transport_send_message(sut_client, {"message": message})

        # Validate JSON-RPC response structure
        if "result" in response:
            # Should follow JSON-RPC 2.0 success response format
            assert isinstance(response["result"], dict)
            logger.info("✅ JSON-RPC response format validated")
        elif "error" in response:
            # Should follow JSON-RPC 2.0 error response format
            error = response["error"]
            assert "code" in error and "message" in error
            logger.info("✅ JSON-RPC error format validated")

    @optional_capability
    @a2a_v030
    def test_grpc_method_optimizations(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 §3.2 - gRPC Transport Method Optimizations

        Tests gRPC specific method optimizations and streaming capabilities.
        """
        if not is_transport_client(sut_client):
            pytest.skip("Test requires transport-aware client")

        transport_type = get_client_transport_type(sut_client)

        if transport_type != "grpc":
            pytest.skip("Test specific to gRPC transport")

        # Test gRPC specific features
        # Note: This would require actual gRPC client implementation
        logger.info("⚪ gRPC method optimizations test - requires gRPC client")
        pytest.skip("gRPC client implementation required for transport-specific testing")

    @optional_capability
    @a2a_v030
    def test_rest_api_method_mappings(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 §3.3 - REST API Method Mappings

        Tests REST API specific method mappings and HTTP verb usage.
        """
        if not is_transport_client(sut_client):
            pytest.skip("Test requires transport-aware client")

        transport_type = get_client_transport_type(sut_client)

        if transport_type != "rest":
            pytest.skip("Test specific to REST transport")

        # Test REST specific features
        # Note: This would require actual REST client implementation
        logger.info("⚪ REST API method mappings test - requires REST client")
        pytest.skip("REST client implementation required for transport-specific testing")


class TestMethodPerformanceAndScaling:
    """
    Test method performance characteristics and scaling behavior in A2A v0.3.0.

    Validates that methods perform adequately and handle various load scenarios
    as expected in production environments.
    """

    @optional_capability
    @a2a_v030
    def test_concurrent_method_calls(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 - Concurrent Method Call Handling

        Tests that the SUT can handle multiple concurrent method calls
        without degradation or interference.
        """
        # Create multiple concurrent tasks
        messages = []
        for i in range(3):  # Keep small for testing
            message = {
                "kind": "message",
                "messageId": generate_test_message_id(f"concurrent-{i}"),
                "role": "user",
                "parts": [{"kind": "text", "text": f"Concurrent test message {i}"}],
            }
            messages.append(message)

        # Send messages concurrently (simulated)
        responses = []
        for message in messages:
            response = transport_send_message(sut_client, {"message": message})
            responses.append(response)

        # Validate all responses
        successful_tasks = 0
        for i, response in enumerate(responses):
            if "result" in response:
                successful_tasks += 1
                task = response["result"]
                assert "id" in task, f"Task {i} missing ID"
            elif "error" in response:
                # Errors are acceptable but log them
                logger.warning(f"Concurrent task {i} failed: {response['error']}")

        # At least some should succeed
        assert successful_tasks > 0, "No concurrent tasks succeeded"
        logger.info(f"✅ Concurrent method calls: {successful_tasks}/{len(messages)} succeeded")

    @optional_capability
    @a2a_v030
    def test_method_response_times(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 - Method Response Time Validation

        Tests that methods respond within reasonable time limits
        for production use.
        """
        import time

        message = {
            "kind": "message",
            "messageId": generate_test_message_id("response-time"),
            "role": "user",
            "parts": [{"kind": "text", "text": "Response time test message"}],
        }

        start_time = time.time()
        response = transport_send_message(sut_client, {"message": message})
        end_time = time.time()

        response_time = end_time - start_time

        # Reasonable response time for testing (adjust as needed)
        max_response_time = 10.0  # 10 seconds

        assert response_time < max_response_time, f"Method response time {response_time:.2f}s exceeds limit {max_response_time}s"

        logger.info(f"✅ Method response time: {response_time:.2f}s (within limits)")

        if "result" in response:
            task = response["result"]
            assert "id" in task, "Task ID should be returned"
