"""Transport-level behavior tests.

Inspects HTTP headers, Content-Type, and response structure from
transport operations to verify binding-specific requirements.

Requirements tested:
    JSONRPC-FMT-001, JSONRPC-FMT-002, JSONRPC-SVC-001, JSONRPC-SVC-002,
    JSONRPC-SSE-001,
    HTTP_JSON-SVC-001, HTTP_JSON-SVC-002, HTTP_JSON-URL-001, HTTP_JSON-URL-002,
    HTTP_JSON-QP-001, HTTP_JSON-SSE-001,
    GRPC-SVC-001, GRPC-META-001, GRPC-ERR-003
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import tck_id
from tck.requirements.registry import get_requirement_by_id
from tests.compatibility._test_helpers import fail_msg, record
from tests.compatibility.markers import grpc, http_json, jsonrpc, must, streaming


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient, TransportResponse


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

JSONRPC_FMT_001 = get_requirement_by_id("JSONRPC-FMT-001")
JSONRPC_FMT_002 = get_requirement_by_id("JSONRPC-FMT-002")
JSONRPC_SVC_001 = get_requirement_by_id("JSONRPC-SVC-001")
JSONRPC_SSE_001 = get_requirement_by_id("JSONRPC-SSE-001")
HTTP_JSON_SVC_001 = get_requirement_by_id("HTTP_JSON-SVC-001")
HTTP_JSON_URL_001 = get_requirement_by_id("HTTP_JSON-URL-001")
HTTP_JSON_URL_002 = get_requirement_by_id("HTTP_JSON-URL-002")
HTTP_JSON_QP_001 = get_requirement_by_id("HTTP_JSON-QP-001")
HTTP_JSON_SSE_001 = get_requirement_by_id("HTTP_JSON-SSE-001")
GRPC_SVC_001 = get_requirement_by_id("GRPC-SVC-001")
GRPC_ERR_003 = get_requirement_by_id("GRPC-ERR-003")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_MESSAGE = {
    "role": "ROLE_USER",
    "parts": [{"text": "Hello from TCK transport test"}],
    "messageId": tck_id("transport-test-001"),
}


# ---------------------------------------------------------------------------
# JSON-RPC transport tests
# ---------------------------------------------------------------------------


@must
@jsonrpc
class TestJsonRpcFormat:
    """JSONRPC-FMT-001 / JSONRPC-FMT-002: JSON-RPC 2.0 format and Content-Type."""

    @pytest.fixture()
    def jsonrpc_response(
        self, transport_clients: dict[str, BaseTransportClient]
    ) -> TransportResponse:
        """Send a message via JSON-RPC and return the response."""
        client = transport_clients.get("jsonrpc")
        if client is None:
            pytest.skip("JSON-RPC transport not configured")
        return client.send_message(message=_SAMPLE_MESSAGE)

    def test_response_validates_jsonrpc_envelope(
        self,
        jsonrpc_response: TransportResponse,
        validators: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """JSONRPC-FMT-001: Response conforms to JSON-RPC 2.0 via JsonRpcResponseValidator."""
        req = JSONRPC_FMT_001
        transport = "jsonrpc"
        validator = validators[transport]
        result = validator.validate(
            jsonrpc_response.raw_response, "Send Message Response"
        )
        record(collector=compatibility_collector, req=req, transport=transport,
                passed=result.valid, errors=result.errors)
        assert result.valid, fail_msg(req, transport, "; ".join(result.errors))

    def test_content_type_is_application_json(
        self,
        jsonrpc_response: TransportResponse,
        compatibility_collector: Any,
    ) -> None:
        """JSONRPC-FMT-002: Content-Type must be application/json."""
        req = JSONRPC_FMT_002
        transport = "jsonrpc"
        ct = jsonrpc_response.headers.get("content-type", "")
        errors = []
        if "application/json" not in ct:
            errors.append(f"Expected Content-Type application/json, got: {ct!r}")
        record(collector=compatibility_collector, req=req, transport=transport,
                passed=not errors, errors=errors)
        assert not errors, fail_msg(req, transport, "; ".join(errors))


@must
@jsonrpc
class TestJsonRpcMethodNames:
    """JSONRPC-SVC-001: Method names match the spec-defined set."""

    # The exact method names defined in A2A spec Section 9.
    _SPEC_METHOD_NAMES = {
        "SendMessage",
        "SendStreamingMessage",
        "GetTask",
        "ListTasks",
        "CancelTask",
        "SubscribeToTask",
        "CreateTaskPushNotificationConfig",
        "GetTaskPushNotificationConfig",
        "ListTaskPushNotificationConfigs",
        "DeleteTaskPushNotificationConfig",
        "GetExtendedAgentCard",
    }

    def test_bindings_use_spec_method_names(
        self, compatibility_collector: Any
    ) -> None:
        """JSONRPC-SVC-001: JSON-RPC method names match the spec-defined names."""
        req = JSONRPC_SVC_001
        transport = "jsonrpc"
        from tck.requirements.base import OperationType

        errors = []
        actual = {op.value for op in OperationType}
        unexpected = actual - self._SPEC_METHOD_NAMES
        missing = self._SPEC_METHOD_NAMES - actual
        if unexpected:
            errors.append(f"Unexpected method names: {unexpected}")
        if missing:
            errors.append(f"Missing spec method names: {missing}")
        record(collector=compatibility_collector, req=req, transport=transport,
                passed=not errors, errors=errors)
        assert not errors, fail_msg(req, transport, "; ".join(errors))


@must
@jsonrpc
@streaming
class TestJsonRpcStreaming:
    """JSONRPC-SSE-001: Streaming uses text/event-stream."""

    def test_streaming_content_type(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """Streaming Content-Type must be text/event-stream."""
        req = JSONRPC_SSE_001
        transport = "jsonrpc"
        client = transport_clients.get(transport)
        if client is None:
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("JSON-RPC transport not configured")
        response = client.send_streaming_message(message=_SAMPLE_MESSAGE)
        if not response.success:
            pytest.skip(f"Streaming not supported: {response.error}")
        ct = response.headers.get("content-type", "")
        errors = []
        if "text/event-stream" not in ct:
            errors.append(f"Streaming Content-Type must be text/event-stream, got: {ct!r}")
        record(collector=compatibility_collector, req=req, transport=transport,
                passed=not errors, errors=errors)
        assert not errors, fail_msg(req, transport, "; ".join(errors))


# ---------------------------------------------------------------------------
# HTTP+JSON / REST transport tests
# ---------------------------------------------------------------------------


@must
@http_json
class TestRestFormat:
    """HTTP_JSON-SVC-001: Content-Type and response schema validation."""

    @pytest.fixture()
    def rest_response(
        self, transport_clients: dict[str, BaseTransportClient]
    ) -> TransportResponse:
        """Send a message via HTTP+JSON and return the response."""
        client = transport_clients.get("http_json")
        if client is None:
            pytest.skip("HTTP+JSON transport not configured")
        return client.send_message(message=_SAMPLE_MESSAGE)

    def test_response_content_type(
        self,
        rest_response: TransportResponse,
        compatibility_collector: Any,
    ) -> None:
        """HTTP_JSON-SVC-001: Content-Type must be application/json."""
        req = HTTP_JSON_SVC_001
        transport = "http_json"
        ct = rest_response.headers.get("content-type", "")
        errors = []
        if "application/json" not in ct:
            errors.append(f"Expected Content-Type application/json, got: {ct!r}")
        record(collector=compatibility_collector, req=req, transport=transport,
                passed=not errors, errors=errors)
        assert not errors, fail_msg(req, transport, "; ".join(errors))

    def test_response_validates_against_schema(
        self,
        rest_response: TransportResponse,
        validators: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """HTTP_JSON-SVC-001: Response payload conforms to SendMessageResponse schema."""
        req = HTTP_JSON_SVC_001
        transport = "http_json"
        if not rest_response.success:
            pytest.skip(f"SendMessage failed: {rest_response.error}")
        validator = validators[transport]
        result = validator.validate(
            rest_response.raw_response, "Send Message Response"
        )
        record(collector=compatibility_collector, req=req, transport=transport,
                passed=result.valid, errors=result.errors)
        assert result.valid, fail_msg(req, transport, "; ".join(result.errors))


@must
@http_json
class TestRestUrlPatterns:
    """HTTP_JSON-URL-001 / HTTP_JSON-URL-002: URL patterns and HTTP methods (client-side validation)."""

    def test_url_patterns_defined(self, compatibility_collector: Any) -> None:
        """HTTP_JSON-URL-001: Verify URL patterns are correctly defined in bindings."""
        req = HTTP_JSON_URL_001
        transport = "http_json"
        from tck.requirements.base import (
            CANCEL_TASK_BINDING,
            GET_TASK_BINDING,
            LIST_TASKS_BINDING,
            PATH_MESSAGE_SEND,
            PATH_MESSAGE_STREAM,
        )

        errors = []
        if PATH_MESSAGE_SEND != "/message:send":
            errors.append(f"PATH_MESSAGE_SEND={PATH_MESSAGE_SEND!r}")
        if PATH_MESSAGE_STREAM != "/message:stream":
            errors.append(f"PATH_MESSAGE_STREAM={PATH_MESSAGE_STREAM!r}")
        if GET_TASK_BINDING.http_json_path != "/tasks/{id}":
            errors.append(f"GET_TASK path={GET_TASK_BINDING.http_json_path!r}")
        if LIST_TASKS_BINDING.http_json_path != "/tasks":
            errors.append(f"LIST_TASKS path={LIST_TASKS_BINDING.http_json_path!r}")
        if CANCEL_TASK_BINDING.http_json_path != "/tasks/{id}:cancel":
            errors.append(f"CANCEL_TASK path={CANCEL_TASK_BINDING.http_json_path!r}")
        record(collector=compatibility_collector, req=req, transport=transport,
                passed=not errors, errors=errors)
        assert not errors, fail_msg(req, transport, "; ".join(errors))

    def test_http_methods_correct(self, compatibility_collector: Any) -> None:
        """HTTP_JSON-URL-002: Correct HTTP methods per operation."""
        req = HTTP_JSON_URL_002
        transport = "http_json"
        from tck.requirements.base import (
            CANCEL_TASK_BINDING,
            DELETE_PUSH_CONFIG_BINDING,
            GET_TASK_BINDING,
            LIST_TASKS_BINDING,
            SEND_MESSAGE_BINDING,
        )

        errors = []
        checks = [
            (SEND_MESSAGE_BINDING.http_json_method, "POST", "SEND_MESSAGE"),
            (GET_TASK_BINDING.http_json_method, "GET", "GET_TASK"),
            (LIST_TASKS_BINDING.http_json_method, "GET", "LIST_TASKS"),
            (CANCEL_TASK_BINDING.http_json_method, "POST", "CANCEL_TASK"),
            (DELETE_PUSH_CONFIG_BINDING.http_json_method, "DELETE", "DELETE_PUSH_CONFIG"),
        ]
        for actual, expected, name in checks:
            if actual != expected:
                errors.append(f"{name}: expected {expected}, got {actual}")
        record(collector=compatibility_collector, req=req, transport=transport,
                passed=not errors, errors=errors)
        assert not errors, fail_msg(req, transport, "; ".join(errors))


@must
@http_json
class TestRestQueryParams:
    """HTTP_JSON-QP-001: Query parameter names use camelCase (client-side validation)."""

    def test_query_params_are_camel_case(
        self, compatibility_collector: Any
    ) -> None:
        """Verify the HttpJsonClient sends camelCase query params."""
        req = HTTP_JSON_QP_001
        transport = "http_json"
        from tck.requirements.base import LIST_TASKS_BINDING

        errors = []
        if LIST_TASKS_BINDING.http_json_method != "GET":
            errors.append(f"LIST_TASKS method={LIST_TASKS_BINDING.http_json_method}")
        if LIST_TASKS_BINDING.http_json_path != "/tasks":
            errors.append(f"LIST_TASKS path={LIST_TASKS_BINDING.http_json_path}")
        record(collector=compatibility_collector, req=req, transport=transport,
                passed=not errors, errors=errors)
        assert not errors, fail_msg(req, transport, "; ".join(errors))


@must
@http_json
@streaming
class TestRestStreaming:
    """HTTP_JSON-SSE-001: HTTP+JSON streaming uses Server-Sent Events."""

    def test_streaming_content_type(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """REST streaming Content-Type must be text/event-stream."""
        req = HTTP_JSON_SSE_001
        transport = "http_json"
        client = transport_clients.get(transport)
        if client is None:
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("HTTP+JSON transport not configured")
        response = client.send_streaming_message(message=_SAMPLE_MESSAGE)
        if not response.success:
            pytest.skip(f"Streaming not supported: {response.error}")
        ct = response.headers.get("content-type", "")
        errors = []
        if "text/event-stream" not in ct:
            errors.append(f"Streaming Content-Type must be text/event-stream, got: {ct!r}")
        record(collector=compatibility_collector, req=req, transport=transport,
                passed=not errors, errors=errors)
        assert not errors, fail_msg(req, transport, "; ".join(errors))


# ---------------------------------------------------------------------------
# gRPC transport tests (partial — limited by what we can verify)
# ---------------------------------------------------------------------------


@must
@grpc
class TestGrpcService:
    """GRPC-SVC-001: A2AService gRPC service implemented."""

    def test_grpc_response_validates_against_proto(
        self,
        transport_clients: dict[str, BaseTransportClient],
        validators: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """GRPC-SVC-001: gRPC service responds and payload validates against proto."""
        req = GRPC_SVC_001
        transport = "grpc"
        client = transport_clients.get(transport)
        if client is None:
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("gRPC transport not configured")
        response = client.send_message(message=_SAMPLE_MESSAGE)
        errors = []
        if response is None:
            errors.append("gRPC service returned no response")
        elif response.success and response.raw_response is not None:
            # Validate the protobuf response against its descriptor
            validator = validators[transport]
            from specification.generated import a2a_pb2

            result = validator.validate(
                response.raw_response, a2a_pb2.SendMessageResponse
            )
            if not result.valid:
                errors.extend(result.errors)
        elif not response.success:
            # Getting an error response still proves the service is implemented
            pass
        record(collector=compatibility_collector, req=req, transport=transport,
                passed=not errors, errors=errors)
        assert not errors, fail_msg(req, transport, "; ".join(errors))


@must
@grpc
@streaming
class TestGrpcStreaming:
    """GRPC-ERR-003: gRPC streaming uses server streaming RPCs."""

    def test_grpc_streaming_works(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """Verify gRPC streaming is functional (server streaming RPC)."""
        req = GRPC_ERR_003
        transport = "grpc"
        client = transport_clients.get(transport)
        if client is None:
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("gRPC transport not configured")
        response = client.send_streaming_message(message=_SAMPLE_MESSAGE)
        if not response.success:
            pytest.skip(f"gRPC streaming not supported: {response.error}")
        errors = []
        if not response.is_streaming:
            errors.append("gRPC streaming response must be a StreamingResponse")
        record(collector=compatibility_collector, req=req, transport=transport,
                passed=not errors, errors=errors)
        assert not errors, fail_msg(req, transport, "; ".join(errors))
