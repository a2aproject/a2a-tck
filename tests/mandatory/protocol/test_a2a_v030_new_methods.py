"""
A2A v0.3.0+ New Methods Testing

Tests for new methods introduced in A2A v0.3.0 specification:
- agent/getAuthenticatedExtendedCard (§7.10)
- ListTasks (§3.1.4 - ALL transports as of v1.0)
- Method mapping compliance across transports (§3.5.6)
- Transport-specific features validation

These tests validate that SUTs correctly implement the new methods
with proper authentication, transport mapping, and functional compliance.

Note: For comprehensive ListTasks testing, see test_tasks_list_method.py

References:
- A2A v0.3.0 Specification §7.10: agent/getAuthenticatedExtendedCard
- A2A v1.0 Specification §3.1.4: ListTasks (all transports)
- A2A v0.3.0 Specification §3.5.6: Method Mapping Reference Table
- A2A v0.3.0 Specification §3.2: Transport Protocol Requirements
"""

import logging
import pytest
from typing import Dict, Any, List, Optional, Union

from tck.transport.base_client import BaseTransportClient
from tck.transport.jsonrpc_client import JSONRPCClient
from tck.transport.grpc_client import GRPCClient
from tck.transport.rest_client import RESTClient
from tests.markers import mandatory_protocol, optional_capability, a2a_v030
from tests.utils.transport_helpers import (
    transport_send_message,
    transport_get_task,
    transport_cancel_task,
    transport_get_extended_agent_card,
    is_transport_client,
    get_client_transport_type,
    generate_test_message_id,
)

logger = logging.getLogger(__name__)

class TestAuthenticatedExtendedCard:
    """
    Test suite for agent/getAuthenticatedExtendedCard method (§7.10)

    Validates that SUTs correctly implement authenticated agent card retrieval
    with proper authentication requirements and extended card functionality.
    """

    @pytest.mark.mandatory
    @pytest.mark.mandatory_protocol
    @pytest.mark.a2a_v030
    def test_authenticated_extended_card_method_exists(self, sut_client: BaseTransportClient, agent_card_data):
        """
        Test that agent/getAuthenticatedExtendedCard method exists and is callable.

        A2A v0.3.0 Specification Reference: §7.10
        Transport Support: All transports (JSON-RPC, gRPC, REST)

        Validates:
        - Method is available on all supported transports
        - Method follows correct naming conventions per transport
        - Authentication is properly enforced
        """
        # Check if agent card supports authenticated extended card
        if not agent_card_data.get("supportsAuthenticatedExtendedCard", False):
            pytest.skip("SUT does not support authenticated extended card")

        # Test method existence based on transport type
        transport_type = get_client_transport_type(sut_client)

        if transport_type == "jsonrpc":
            # JSON-RPC: agent/getAuthenticatedExtendedCard method
            try:
                response = transport_get_extended_agent_card(sut_client)
                assert "result" in response or "error" in response

                # If error, should be authentication-related (401/403)
                if "error" in response:
                    error_code = response["error"]["code"]
                    # Expect authentication errors for unauthenticated requests
                    assert error_code in [-32007, -32603], f"Unexpected error code: {error_code}"

            except Exception as e:
                pytest.fail(f"Failed to call agent/getAuthenticatedExtendedCard: {e}")

        elif transport_type == "grpc":
            # gRPC: GetAgentCard method
            try:
                # For gRPC, the method should exist as GetAgentCard
                response = sut_client.get_extended_agent_card()
                assert response is not None

            except Exception as e:
                # Should get authentication error for unauthenticated request
                assert "authentication" in str(e).lower() or "unauthorized" in str(e).lower()

        elif transport_type == "rest":
            # REST: GET /v1/card
            try:
                response = sut_client.get_extended_agent_card()
                assert response is not None

            except Exception as e:
                # Should get authentication error for unauthenticated request
                assert "401" in str(e) or "403" in str(e) or "authentication" in str(e).lower()

    @pytest.mark.mandatory
    @pytest.mark.mandatory_protocol
    @pytest.mark.a2a_v030
    def test_authenticated_extended_card_without_auth(self, sut_client: BaseTransportClient, agent_card_data):
        """
        Test that agent/getAuthenticatedExtendedCard properly rejects unauthenticated requests.

        A2A v0.3.0 Specification Reference: §7.10

        Validates:
        - Unauthenticated requests return 401 Unauthorized
        - Proper WWW-Authenticate header is included (when applicable)
        - Error response follows A2A error format
        """
        # Check if SUT supports authenticated extended card
        if not agent_card_data.get("supportsAuthenticatedExtendedCard", False):
            pytest.skip("SUT does not support authenticated extended card")

        # Test without authentication credentials
        transport_type = get_client_transport_type(sut_client)

        if transport_type == "jsonrpc":
            # Clear any existing authentication headers
            original_headers = getattr(sut_client, "headers", {})
            try:
                if hasattr(sut_client, "headers"):
                    # Remove auth headers temporarily
                    auth_headers = ["authorization", "x-api-key", "authentication"]
                    for header in auth_headers:
                        sut_client.headers.pop(header, None)
                        sut_client.headers.pop(header.title(), None)
                        sut_client.headers.pop(header.upper(), None)

                response = transport_get_extended_agent_card(sut_client)

                # Should return error
                assert "error" in response
                error = response["error"]

                # Should be authentication-related error
                assert error["code"] in [-32007, -32603], f"Expected auth error, got: {error}"

            finally:
                # Restore original headers
                if hasattr(sut_client, "headers"):
                    sut_client.headers.update(original_headers)

        else:
            # For gRPC/REST, test without auth should fail
            with pytest.raises(Exception) as exc_info:
                sut_client.get_extended_agent_card()

            error_msg = str(exc_info.value).lower()
            assert any(keyword in error_msg for keyword in ["unauthorized", "authentication", "401", "403"]), (
                f"Expected authentication error, got: {exc_info.value}"
            )

    @optional_capability
    @a2a_v030
    def test_authenticated_extended_card_with_auth(self, sut_client: BaseTransportClient, agent_card_data):
        """
        Test that agent/getAuthenticatedExtendedCard returns extended card with valid auth.

        A2A v0.3.0 Specification Reference: §7.10 & §11.1.3

        Validates:
        - Authenticated requests return AgentCard object
        - Extended card may contain additional details
        - Response follows AgentCard schema

        CAPABILITY-DEPENDENT: This test is MANDATORY if supportsAuthenticatedExtendedCard: true
        is declared in the Agent Card, otherwise it's skipped. This prevents false advertising
        where agents claim to support authenticated extended cards but don't implement them properly.
        """
        # Check if SUT supports authenticated extended card
        if not agent_card_data.get("supportsAuthenticatedExtendedCard", False):
            pytest.skip("SUT does not support authenticated extended card")

        # Skip if no authentication is configured
        if not hasattr(sut_client, "headers") or not any(
            key.lower() in ["authorization", "x-api-key", "authentication"] for key in getattr(sut_client, "headers", {}).keys()
        ):
            pytest.skip("No authentication credentials configured for testing")

        try:
            extended_card = sut_client.get_extended_agent_card()

            # Validate it's a proper AgentCard
            assert isinstance(extended_card, dict)
            assert "protocolVersion" in extended_card
            assert "name" in extended_card
            assert "description" in extended_card
            assert "url" in extended_card
            assert "skills" in extended_card
            assert "capabilities" in extended_card

            # Should be version 0.3.0 or compatible
            protocol_version = extended_card["protocolVersion"]
            assert protocol_version.startswith("0.3"), f"Expected v0.3.x, got: {protocol_version}"

        except Exception as e:
            if "authentication" in str(e).lower() or "401" in str(e) or "403" in str(e):
                pytest.skip("Authentication credentials not accepted by SUT")
            else:
                pytest.fail(f"Failed to get authenticated extended card: {e}")


class TestTasksList:
    """
    Test suite for ListTasks method (§3.1.4)

    Note: As of A2A v1.0, ListTasks is available in ALL transports including JSON-RPC.
    For comprehensive testing, see test_tasks_list_method.py
    """


    @optional_capability
    @a2a_v030
    def test_tasks_list_with_existing_tasks(self, sut_client: BaseTransportClient):
        """
        Test ListTasks returns existing tasks when tasks are present.

        A2A v1.0 Specification Reference: §3.1.4
        Transport Support: All transports (JSON-RPC, gRPC, REST)

        Validates:
        - List includes previously created tasks
        - Task objects follow proper schema
        - List is properly formatted

        Note: This is a basic smoke test. See test_tasks_list_method.py for comprehensive testing.
        """
        if not hasattr(sut_client, "list_tasks"):
            pytest.fail(f"list_tasks method not implemented on client - this is MANDATORY for A2A v1.0 compliance")

        # Create a task first
        try:
            task = transport_send_message(sut_client, "Test message for task listing")
            created_task_id = task["id"]

            # Now list tasks
            tasks = sut_client.list_tasks()
            assert isinstance(tasks, list)

            # Should include our created task
            task_ids = [t["id"] for t in tasks]
            assert created_task_id in task_ids, f"Created task {created_task_id} not found in list"

            # Validate task structure
            our_task = next(t for t in tasks if t["id"] == created_task_id)
            assert "status" in our_task
            assert "contextId" in our_task

        except Exception as e:
            pytest.fail(f"Failed to test ListTasks with existing tasks: {e}")


class TestMethodMappingCompliance:
    """
    Test suite for method mapping compliance across transports (§3.5.6)

    Validates that all supported transports follow the correct method naming
    conventions as specified in the A2A v0.3.0 Method Mapping Reference Table.
    """

    @pytest.mark.mandatory
    @pytest.mark.mandatory_protocol
    @pytest.mark.a2a_v030
    def test_core_method_mapping_compliance(self, sut_client: BaseTransportClient):
        """
        Test that core A2A methods follow correct naming conventions per transport.

        A2A v0.3.0 Specification Reference: §3.5.6 Method Mapping Reference Table

        Validates mapping for:
        - SendMessage → SendMessage → POST /v1/message:send
        - tasks/get → GetTask → GET /v1/tasks/{id}
        - tasks/cancel → CancelTask → POST /v1/tasks/{id}:cancel
        """
        transport_type = get_client_transport_type(sut_client)

        # Test SendMessage mapping
        try:
            sample_message = {
                "messageId": generate_test_message_id("mapping-test"),
                "role": "ROLE_USER",
                "parts": [{"text": "Method mapping test"}],
            }
            response = transport_send_message(sut_client, {"message": sample_message})
            assert response is not None
            # Extract task from response
            if "result" in response and isinstance(response["result"], dict):
                task = response["result"]["task"]
            else:
                task = response["task"]
            assert "id" in task
            task_id = task["id"]

            # Test tasks/get mapping
            get_response = transport_get_task(sut_client, task_id)
            assert get_response is not None
            retrieved_task = get_response["result"]
            assert retrieved_task["id"] == task_id

            # Test tasks/cancel mapping
            cancel_response = transport_cancel_task(sut_client, task_id)
            assert cancel_response is not None
            cancelled_task = cancel_response["result"]
            assert cancelled_task["id"] == task_id

        except Exception as e:
            pytest.fail(f"Core method mapping test failed on {transport_type}: {e}")

    @pytest.mark.mandatory
    @pytest.mark.mandatory_protocol
    @pytest.mark.a2a_v030
    def test_transport_specific_method_naming(self, sut_client: BaseTransportClient):
        """
        Test that transport-specific method naming follows A2A v1.0 conventions.

        A2A v1.0 Specification Reference: §5.3. Method Mapping Reference

        Validates:
        - JSON-RPC: PascalCase compound words
        - gRPC: PascalCase compound words
        - REST: /v1/{resource}[/{id}][:{action}] pattern
        """
        transport_type = get_client_transport_type(sut_client)

        if transport_type == "jsonrpc" or transport_type == "grpc":
            # Test gRPC & JSON-RPC PascalCase naming
            if hasattr(sut_client, "_get_method_mapping"):
                method_mapping = sut_client._get_method_mapping()
                for grpc_method in method_mapping.values():
                    # Should be PascalCase
                    assert grpc_method[0].isupper(), f"gRPC method {grpc_method} should start with uppercase"
                    assert grpc_method.replace("_", "").isalnum(), f"gRPC method {grpc_method} should be alphanumeric"

        elif transport_type == "rest":
            # Test REST URL pattern compliance
            if hasattr(sut_client, "_get_url_patterns"):
                url_patterns = sut_client._get_url_patterns()
                for pattern in url_patterns.values():
                    # Should start with /v1/
                    assert pattern.startswith("/v1/"), f"REST URL {pattern} should start with /v1/"

                    # Should follow resource-based pattern
                    if ":send" in pattern:
                        assert "/message:send" in pattern
                    elif ":cancel" in pattern:
                        assert "/tasks/" in pattern and ":cancel" in pattern


class TestTransportSpecificFeatures:
    """
    Test suite for transport-specific features and optimizations (§3.4.3)

    Validates that transports provide transport-specific extensions while
    maintaining functional equivalence with core A2A functionality.
    """

    @optional_capability
    @a2a_v030
    def test_grpc_specific_features(self, sut_client: BaseTransportClient):
        """
        Test gRPC-specific features like bidirectional streaming and metadata.

        A2A v0.3.0 Specification Reference: §3.4.3 (Transport-Specific Extensions)

        Validates:
        - Bidirectional streaming support (if implemented)
        - gRPC metadata handling
        - Protocol Buffers serialization

        TRANSPORT-DEPENDENT: This test is MANDATORY if gRPC transport is declared in
        Agent Card additionalInterfaces, ensuring transport-specific optimizations
        maintain functional equivalence.
        """
        if get_client_transport_type(sut_client) != "grpc":
            pytest.skip("Test only applicable to gRPC transport")

        # Test gRPC metadata support
        if hasattr(sut_client, "send_message_with_metadata"):
            try:
                metadata = {"custom-header": "test-value"}
                task = sut_client.send_message_with_metadata("Test message with metadata", metadata=metadata)
                assert task is not None

            except Exception as e:
                if "not implemented" in str(e).lower():
                    pytest.skip("gRPC metadata not implemented")
                else:
                    pytest.fail(f"gRPC metadata test failed: {e}")

        # Test bidirectional streaming (if supported)
        if hasattr(sut_client, "bidirectional_stream"):
            try:
                # Test basic bidirectional streaming capability
                stream = sut_client.bidirectional_stream()
                assert stream is not None

            except Exception as e:
                if "not implemented" in str(e).lower():
                    pytest.skip("gRPC bidirectional streaming not implemented")
                else:
                    pytest.fail(f"gRPC bidirectional streaming test failed: {e}")

    @optional_capability
    @a2a_v030
    def test_rest_specific_features(self, sut_client: BaseTransportClient):
        """
        Test REST-specific features like HTTP caching and conditional requests.

        A2A v0.3.0 Specification Reference: §3.4.3

        Validates:
        - HTTP caching headers
        - Conditional request support (If-Modified-Since, ETag)
        - Proper HTTP status codes
        """
        if get_client_transport_type(sut_client) != "rest":
            pytest.skip("Test only applicable to REST transport")

        # Test HTTP caching headers
        if hasattr(sut_client, "get_with_caching"):
            try:
                response = sut_client.get_with_caching("/v1/card")

                # Should include caching headers
                headers = getattr(response, "headers", {})
                cache_headers = ["cache-control", "etag", "last-modified"]

                has_cache_header = any(header in headers for header in cache_headers)
                if not has_cache_header:
                    # Not required, but note if missing
                    pass

            except Exception as e:
                if "not implemented" in str(e).lower():
                    pytest.skip("REST caching features not implemented")
                else:
                    pytest.fail(f"REST caching test failed: {e}")

        # Test conditional requests
        if hasattr(sut_client, "conditional_get"):
            try:
                # First request to get ETag/Last-Modified
                response1 = sut_client.get_extended_agent_card()

                # Second request with conditional headers
                response2 = sut_client.conditional_get("/extendedAgentCard")

                # Should handle conditional requests appropriately
                assert response2 is not None

            except Exception as e:
                if "not implemented" in str(e).lower():
                    pytest.skip("REST conditional requests not implemented")
                else:
                    pytest.fail(f"REST conditional request test failed: {e}")

    @optional_capability
    @a2a_v030
    def test_jsonrpc_specific_features(self, sut_client: BaseTransportClient):
        """
        Test JSON-RPC-specific features and extensions.

        A2A v0.3.0 Specification Reference: §3.4.3

        Validates:
        - Additional fields in JSON-RPC objects (non-conflicting)
        - Batch request support (if implemented)
        - JSON-RPC 2.0 compliance
        """
        if get_client_transport_type(sut_client) != "jsonrpc":
            pytest.skip("Test only applicable to JSON-RPC transport")

        # Test batch requests (if supported)
        if hasattr(sut_client, "batch_request"):
            try:
                batch_requests = [
                    {"method": "agent/getCard", "params": {}, "id": 1},
                    {
                        "method": "SendMessage",
                        "params": {
                            "message": {"role": "ROLE_USER", "parts": [{"text": "test"}], "messageId": "test-batch-1"}
                        },
                        "id": 2,
                    },
                ]

                responses = sut_client.batch_request(batch_requests)
                assert isinstance(responses, list)
                assert len(responses) == len(batch_requests)

            except Exception as e:
                if "not implemented" in str(e).lower():
                    pytest.skip("JSON-RPC batch requests not implemented")
                else:
                    pytest.fail(f"JSON-RPC batch request test failed: {e}")

        # Test additional fields in responses (should not break spec compliance)
        try:
            message_params = {
                "message": {
                    "role": "ROLE_USER",
                    "parts": [{"text": "Test for additional fields"}],
                    "messageId": "test-additional-fields",
                }
            }
            response = transport_send_message(sut_client, message_params)
            task = response.get("result", {}).get("task", {})

            # Task may have additional fields beyond spec
            spec_fields = {"id", "contextId", "status", "history", "artifacts", "metadata"}
            task_fields = set(task.keys())

            # Additional fields are allowed as long as spec fields are present
            missing_required = {"id", "status"} - task_fields
            assert not missing_required, f"Missing required fields: {missing_required}"

        except Exception as e:
            pytest.fail(f"JSON-RPC additional fields test failed: {e}")
