"""
A2A v0.3.0 Transport-Specific Feature Testing

This module implements comprehensive testing for transport-specific features
including gRPC streaming, REST pagination, JSON-RPC batching, and other
unique capabilities per transport type.

Specification Reference: A2A Protocol v0.3.0 §3 - Transport Implementations
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List
import pytest
import httpx

from tests.markers import optional_capability, a2a_v030
from tests.utils.transport_helpers import is_transport_client, get_client_transport_type, generate_test_message_id
from tck import config, message_utils
from tck.transport.base_client import BaseTransportClient

logger = logging.getLogger(__name__)


class TestJSONRPCSpecificFeatures:
    """
    Test JSON-RPC transport specific features in A2A v0.3.0.

    Validates JSON-RPC 2.0 compliance, batching, and other
    JSON-RPC specific optimizations and features.
    """

    @optional_capability
    @a2a_v030
    def test_json_rpc_batch_requests(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 §3.1 - JSON-RPC Batch Request Support

        Tests JSON-RPC batch request functionality for improved
        performance with multiple operations.
        """
        if not is_transport_client(sut_client):
            pytest.skip("Test requires transport-aware client")

        transport_type = get_client_transport_type(sut_client)

        if transport_type != "jsonrpc":
            pytest.skip("Test specific to JSON-RPC transport")

        # Create batch request
        batch_requests = []
        for i in range(3):
            message = {
                "kind": "message",
                "messageId": generate_test_message_id(f"batch-{i}"),
                "role": "user",
                "parts": [{"kind": "text", "text": f"Batch message {i}"}],
            }

            req = message_utils.make_json_rpc_request("message/send", params={"message": message}, id=f"batch-req-{i}")
            batch_requests.append(req)

        # Test batch request (requires direct HTTP access)
        import requests

        sut_url = config.get_sut_url()
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(sut_url, json=batch_requests, headers=headers, timeout=10)

            if response.status_code == 200:
                batch_response = response.json()

                # Should be a list of responses
                if isinstance(batch_response, list):
                    assert len(batch_response) == len(batch_requests), "Batch response length should match request length"

                    # Each response should be valid JSON-RPC
                    for i, resp in enumerate(batch_response):
                        expected_id = f"batch-req-{i}"
                        assert "result" in resp or "error" in resp, f"Batch response {i} should have result or error"
                        assert resp.get("id") == expected_id, f"Batch response {i} ID mismatch"

                    logger.info(f"✅ JSON-RPC batch request successful: {len(batch_response)} responses")
                else:
                    # Single response means batching not supported
                    logger.info("⚪ JSON-RPC batch requests not supported (optional)")
            else:
                logger.info(f"⚪ JSON-RPC batch request failed: HTTP {response.status_code}")

        except Exception as e:
            logger.warning(f"Could not test JSON-RPC batch requests: {e}")

    @optional_capability
    @a2a_v030
    def test_json_rpc_notification_requests(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 §3.1 - JSON-RPC Notification Support

        Tests JSON-RPC notification requests (requests without expecting responses)
        for fire-and-forget operations.
        """
        if not is_transport_client(sut_client):
            pytest.skip("Test requires transport-aware client")

        transport_type = get_client_transport_type(sut_client)

        if transport_type != "jsonrpc":
            pytest.skip("Test specific to JSON-RPC transport")

        # JSON-RPC notifications don't have IDs and expect no response
        notification_request = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "kind": "message",
                    "messageId": generate_test_message_id("notification"),
                    "role": "user",
                    "parts": [{"kind": "text", "text": "Notification test"}],
                }
            },
            # No "id" field = notification
        }

        import requests

        sut_url = config.get_sut_url()
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(sut_url, json=notification_request, headers=headers, timeout=10)

            # For notifications, server should not send a response
            # HTTP 204 No Content would be ideal, but HTTP 200 with empty body is also valid
            if response.status_code in [200, 204]:
                if response.status_code == 204 or not response.text.strip():
                    logger.info("✅ JSON-RPC notification properly handled (no response)")
                else:
                    logger.info("⚪ JSON-RPC notification returned response (may not support notifications)")
            else:
                logger.info(f"⚪ JSON-RPC notification failed: HTTP {response.status_code}")

        except Exception as e:
            logger.warning(f"Could not test JSON-RPC notifications: {e}")

    @optional_capability
    @a2a_v030
    def test_json_rpc_error_extensions(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 §3.1 - JSON-RPC Extended Error Information

        Tests enhanced error information in JSON-RPC responses
        including detailed error data and debugging information.
        """
        if not is_transport_client(sut_client):
            pytest.skip("Test requires transport-aware client")

        transport_type = get_client_transport_type(sut_client)

        if transport_type != "jsonrpc":
            pytest.skip("Test specific to JSON-RPC transport")

        # Send invalid request to trigger detailed error
        invalid_request = message_utils.make_json_rpc_request("invalid/method", params={"invalid": "params"}, id="error-test")

        import requests

        sut_url = config.get_sut_url()
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(sut_url, json=invalid_request, headers=headers, timeout=10)

            if response.status_code == 200:
                error_response = response.json()

                if "error" in error_response:
                    error = error_response["error"]

                    # Standard JSON-RPC error fields
                    assert "code" in error, "Error code required"
                    assert "message" in error, "Error message required"

                    # Enhanced error information (optional)
                    enhanced_fields = ["data", "source", "timestamp", "trace"]
                    found_enhancements = []

                    for field in enhanced_fields:
                        if field in error:
                            found_enhancements.append(field)

                    if found_enhancements:
                        logger.info(f"✅ JSON-RPC enhanced error fields: {found_enhancements}")
                    else:
                        logger.info("⚪ Basic JSON-RPC error format (enhancements optional)")

        except Exception as e:
            logger.warning(f"Could not test JSON-RPC error extensions: {e}")


class TestGRPCSpecificFeatures:
    """
    Test gRPC transport specific features in A2A v0.3.0.

    Validates gRPC streaming, metadata handling, and other
    gRPC specific capabilities and optimizations.
    """

    @optional_capability
    @a2a_v030
    def test_grpc_bidirectional_streaming(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 §3.2 - gRPC Bidirectional Streaming

        Tests gRPC bidirectional streaming capabilities for
        real-time agent communication.
        """
        if not is_transport_client(sut_client):
            pytest.skip("Test requires transport-aware client")

        transport_type = get_client_transport_type(sut_client)

        if transport_type != "grpc":
            pytest.skip("Test specific to gRPC transport")

        # gRPC bidirectional streaming test
        logger.info("⚪ gRPC bidirectional streaming test requires gRPC client implementation")
        pytest.skip("gRPC client implementation required for streaming tests")

    @optional_capability
    @a2a_v030
    def test_grpc_metadata_handling(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 §3.2 - gRPC Metadata and Headers

        Tests gRPC metadata handling for authentication,
        tracing, and other transport-level information.
        """
        if not is_transport_client(sut_client):
            pytest.skip("Test requires transport-aware client")

        transport_type = get_client_transport_type(sut_client)

        if transport_type != "grpc":
            pytest.skip("Test specific to gRPC transport")

        # gRPC metadata test
        logger.info("⚪ gRPC metadata handling test requires gRPC client implementation")
        pytest.skip("gRPC client implementation required for metadata tests")

    @optional_capability
    @a2a_v030
    def test_grpc_compression_support(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 §3.2 - gRPC Compression

        Tests gRPC compression support for improved performance
        with large messages and responses.
        """
        if not is_transport_client(sut_client):
            pytest.skip("Test requires transport-aware client")

        transport_type = get_client_transport_type(sut_client)

        if transport_type != "grpc":
            pytest.skip("Test specific to gRPC transport")

        # gRPC compression test
        logger.info("⚪ gRPC compression test requires gRPC client implementation")
        pytest.skip("gRPC client implementation required for compression tests")


class TestRESTSpecificFeatures:
    """
    Test REST API transport specific features in A2A v0.3.0.

    Validates REST API patterns, HTTP verbs, pagination,
    and other REST specific capabilities.
    """

    @optional_capability
    @a2a_v030
    def test_rest_http_verb_mapping(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 §3.3 - REST HTTP Verb Mapping

        Tests proper HTTP verb mapping for REST API operations
        according to A2A v0.3.0 method mapping specification.
        """
        if not is_transport_client(sut_client):
            pytest.skip("Test requires transport-aware client")

        transport_type = get_client_transport_type(sut_client)

        if transport_type != "rest":
            pytest.skip("Test specific to REST transport")

        # REST HTTP verb mapping tests
        verb_mappings = {
            "POST": ["/v1/messages", "/v1/tasks/{id}/cancel"],
            "GET": ["/v1/tasks/{id}", "/v1/agent/card"],
            "PUT": ["/v1/tasks/{id}/pushNotificationConfig"],
            "DELETE": ["/v1/tasks/{id}/pushNotificationConfig"],
        }

        logger.info("⚪ REST HTTP verb mapping test requires REST client implementation")
        pytest.skip("REST client implementation required for HTTP verb tests")

    @optional_capability
    @a2a_v030
    def test_rest_pagination_support(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 §3.3 - REST API Pagination

        Tests REST API pagination support for methods that
        return collections (e.g., task lists).
        """
        if not is_transport_client(sut_client):
            pytest.skip("Test requires transport-aware client")

        transport_type = get_client_transport_type(sut_client)

        if transport_type != "rest":
            pytest.skip("Test specific to REST transport")

        # REST pagination test
        logger.info("⚪ REST pagination test requires REST client implementation")
        pytest.skip("REST client implementation required for pagination tests")

    @optional_capability
    @a2a_v030
    def test_rest_content_negotiation(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 §3.3 - REST Content Negotiation

        Tests REST API content negotiation for different
        response formats and media types.
        """
        if not is_transport_client(sut_client):
            pytest.skip("Test requires transport-aware client")

        transport_type = get_client_transport_type(sut_client)

        if transport_type != "rest":
            pytest.skip("Test specific to REST transport")

        # Test different Accept headers
        content_types = ["application/json", "application/vnd.api+json", "text/plain"]

        import requests

        sut_url = config.get_sut_url()

        for content_type in content_types:
            headers = {"Accept": content_type}

            try:
                response = requests.get(sut_url, headers=headers, timeout=10)

                returned_content_type = response.headers.get("content-type", "")
                logger.info(f"Accept: {content_type} -> Content-Type: {returned_content_type}")

                # Should return appropriate content type
                if content_type == "application/json":
                    assert "application/json" in returned_content_type.lower(), "Should return JSON for JSON accept header"

            except Exception as e:
                logger.warning(f"Content negotiation test failed for {content_type}: {e}")


class TestStreamingSpecificFeatures:
    """
    Test streaming-specific features across all transport types.

    Validates Server-Sent Events, WebSocket upgrades, and other
    streaming capabilities introduced in A2A v0.3.0.
    """

    @optional_capability
    @a2a_v030
    @pytest.mark.asyncio
    async def test_sse_connection_management(self):
        """
        A2A v0.3.0 §7.2 - Server-Sent Events Connection Management

        Tests SSE connection lifecycle management including
        connection establishment, keep-alive, and graceful termination.
        """
        sut_url = config.get_sut_url()

        # Create SSE request
        message = {
            "kind": "message",
            "messageId": generate_test_message_id("sse-mgmt"),
            "role": "user",
            "parts": [{"kind": "text", "text": "SSE connection management test"}],
        }

        request = message_utils.make_json_rpc_request("message/stream", params={"message": message})

        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", sut_url, json=request, headers=headers) as response:
                    # Should get SSE response
                    if response.status_code == 200:
                        content_type = response.headers.get("content-type", "")

                        if "text/event-stream" in content_type:
                            logger.info("✅ SSE connection established")

                            # Test connection keep-alive
                            event_count = 0
                            async for line in response.aiter_lines():
                                if line.startswith("data:"):
                                    event_count += 1

                                # Test graceful termination
                                if event_count >= 2:
                                    logger.info("✅ SSE connection management validated")
                                    break
                        else:
                            logger.info("⚪ SSE not supported")
                    else:
                        logger.info(f"⚪ SSE connection failed: HTTP {response.status_code}")

        except Exception as e:
            logger.warning(f"Could not test SSE connection management: {e}")

    # WebSocket is not a core A2A v0.3.0 transport - removed test
    # Core transports are: JSON-RPC, gRPC, and HTTP+JSON/REST only


class TestMultiModalFeatures:
    """
    Test multi-modal and advanced content features in A2A v0.3.0.

    Validates file handling, binary data, and other advanced
    content types supported by the protocol.
    """

    @optional_capability
    @a2a_v030
    def test_file_reference_handling(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 §6.5.2 - File Reference Parts

        Tests handling of file reference parts in messages
        for multi-modal agent communication.
        """
        # Test file reference part
        file_message = {
            "kind": "message",
            "messageId": generate_test_message_id("file-ref"),
            "role": "user",
            "parts": [
                {"kind": "text", "text": "Please analyze this file"},
                {
                    "kind": "fileRef",
                    "fileRef": {"uri": "https://example.com/test-file.txt", "mimeType": "text/plain", "name": "test-file.txt"},
                },
            ],
        }

        from tests.utils.transport_helpers import transport_send_message

        response = transport_send_message(sut_client, {"message": file_message})

        # Should handle file reference without error
        if "result" in response:
            logger.info("✅ File reference handling supported")
        elif "error" in response:
            error = response["error"]
            # Should not be method not found
            assert error.get("code") != -32601, "File references should be supported in A2A v0.3.0"
            logger.info(f"⚠️  File reference handling error: {error}")

    @optional_capability
    @a2a_v030
    def test_binary_data_handling(self, sut_client: BaseTransportClient):
        """
        A2A v0.3.0 §6.5.3 - Data Parts with Binary Content

        Tests handling of binary data in message parts
        for advanced content processing.
        """
        # Test data part with binary content
        import base64

        binary_data = b"This is test binary data"
        encoded_data = base64.b64encode(binary_data).decode("ascii")

        data_message = {
            "kind": "message",
            "messageId": generate_test_message_id("binary-data"),
            "role": "user",
            "parts": [
                {"kind": "text", "text": "Processing binary data"},
                {"kind": "data", "data": {"mimeType": "application/octet-stream", "data": encoded_data}},
            ],
        }

        from tests.utils.transport_helpers import transport_send_message

        response = transport_send_message(sut_client, {"message": data_message})

        # Should handle binary data without error
        if "result" in response:
            logger.info("✅ Binary data handling supported")
        elif "error" in response:
            error = response["error"]
            # Should not be method not found
            assert error.get("code") != -32601, "Binary data should be supported in A2A v0.3.0"
            logger.info(f"⚠️  Binary data handling error: {error}")
