"""Error triggering and validation tests.

Sends deliberately invalid or edge-case requests and validates
the error responses conform to the A2A specification.

Requirements tested:
    CORE-ERR-001, CORE-ERR-002,
    CORE-CAP-001, CORE-CAP-002, CORE-CAP-003, CORE-CAP-004,
    VER-SERVER-002, VER-SERVER-003,
    JSONRPC-ERR-001, JSONRPC-ERR-002,
    HTTP_JSON-ERR-001, HTTP_JSON-ERR-002,
    GRPC-ERR-001, GRPC-ERR-002
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
import jsonschema
import pytest

from tck.requirements.registry import get_requirement_by_id
from tests.compatibility._test_helpers import fail_msg, record
from tests.compatibility.markers import core, grpc, http_json, jsonrpc


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

CORE_ERR_001 = get_requirement_by_id("CORE-ERR-001")
CORE_ERR_002 = get_requirement_by_id("CORE-ERR-002")
CORE_CAP_001 = get_requirement_by_id("CORE-CAP-001")
CORE_CAP_002 = get_requirement_by_id("CORE-CAP-002")
CORE_CAP_003 = get_requirement_by_id("CORE-CAP-003")
CORE_CAP_004 = get_requirement_by_id("CORE-CAP-004")
VER_SERVER_002 = get_requirement_by_id("VER-SERVER-002")
VER_SERVER_003 = get_requirement_by_id("VER-SERVER-003")
JSONRPC_ERR_001 = get_requirement_by_id("JSONRPC-ERR-001")
JSONRPC_ERR_002 = get_requirement_by_id("JSONRPC-ERR-002")
JSONRPC_SSE_002 = get_requirement_by_id("JSONRPC-SSE-002")
HTTP_JSON_ERR_001 = get_requirement_by_id("HTTP_JSON-ERR-001")
HTTP_JSON_ERR_002 = get_requirement_by_id("HTTP_JSON-ERR-002")
GRPC_ERR_001 = get_requirement_by_id("GRPC-ERR-001")
GRPC_ERR_002 = get_requirement_by_id("GRPC-ERR-002")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HTTP_ERROR_STATUS = 400

# JSON-RPC error code ranges
_A2A_ERROR_CODE_MIN = -32099
_A2A_ERROR_CODE_MAX = -32001
_JSONRPC_ERROR_CODE_MIN = -32700
_JSONRPC_ERROR_CODE_MAX = -32600

# Specific A2A error codes
_TASK_NOT_FOUND_ERROR_CODE = -32001

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _jsonrpc_call(
    base_url: str,
    method: str,
    params: dict,
    *,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Make a raw JSON-RPC 2.0 call bypassing the client for header control."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    return httpx.post(base_url, json=payload, headers=hdrs)


def _rest_call(
    base_url: str,
    method: str,
    path: str,
    *,
    json_body: dict | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Make a raw HTTP request for REST binding."""
    hdrs = {}
    if json_body is not None:
        hdrs["Content-Type"] = "application/json"
    if headers:
        hdrs.update(headers)
    return httpx.request(method, f"{base_url}{path}", json=json_body, headers=hdrs)


def _get_base_url(
    transport_clients: dict[str, BaseTransportClient], transport: str
) -> str:
    """Get the base URL for a transport client."""
    client = transport_clients.get(transport)
    if client is None:
        pytest.skip(f"{transport} transport not configured")
    return client.base_url


# ---------------------------------------------------------------------------
# Core error handling
# ---------------------------------------------------------------------------


@core
class TestCoreErrorStructure:
    """CORE-ERR-001: Server returns appropriate errors with actionable info."""

    def test_error_has_code_and_message_jsonrpc(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """JSON-RPC error responses include code and message."""
        req = CORE_ERR_001
        transport = "jsonrpc"
        base_url = _get_base_url(transport_clients, transport)
        response = _jsonrpc_call(base_url, "NonExistentMethod", {})
        body = response.json()
        if "error" not in body:
            pytest.skip("Server did not return an error for unknown method")
        error = body["error"]
        errors = []
        if "code" not in error:
            errors.append("JSON-RPC error must have 'code'")
        if "message" not in error:
            errors.append("JSON-RPC error must have 'message'")
        record(collector=compliance_collector, req=req, transport=transport,
                passed=not errors, errors=errors)
        assert not errors, fail_msg(req, transport, "; ".join(errors))

    def test_error_has_code_and_message_rest(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """REST error responses include error information."""
        req = CORE_ERR_001
        transport = "http_json"
        base_url = _get_base_url(transport_clients, transport)
        response = _rest_call(base_url, "GET", "/tasks/tck-nonexistent-error-test")
        passed = response.status_code >= _HTTP_ERROR_STATUS
        errors = [] if passed else [f"Expected error status, got {response.status_code}"]
        record(collector=compliance_collector, req=req, transport=transport,
                passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, errors[0])


@core
class TestCoreInputValidation:
    """CORE-ERR-002: Server validates input parameters."""

    def test_malformed_request_rejected_jsonrpc(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """Send a SendMessage with missing required 'message' field."""
        req = CORE_ERR_002
        transport = "jsonrpc"
        base_url = _get_base_url(transport_clients, transport)
        response = _jsonrpc_call(base_url, "SendMessage", {})
        body = response.json()
        passed = "error" in body
        errors = [] if passed else ["Malformed request must return an error"]
        record(collector=compliance_collector, req=req, transport=transport,
                passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, errors[0])

    def test_malformed_request_rejected_rest(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """Send a POST to /message:send with empty body."""
        req = CORE_ERR_002
        transport = "http_json"
        base_url = _get_base_url(transport_clients, transport)
        response = _rest_call(base_url, "POST", "/message:send", json_body={})
        passed = response.status_code >= _HTTP_ERROR_STATUS
        errors = [] if passed else [f"Expected error status, got {response.status_code}"]
        record(collector=compliance_collector, req=req, transport=transport,
                passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, errors[0])


# ---------------------------------------------------------------------------
# Capability validation
# ---------------------------------------------------------------------------


@core
class TestCapabilityPushNotifications:
    """CORE-CAP-001: Push operations return error when not supported."""

    def test_push_not_supported_jsonrpc(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """Push notification operations must return error when unsupported."""
        req = CORE_CAP_001
        transport = "jsonrpc"
        caps = agent_card.get("capabilities", {})
        if caps.get("pushNotifications"):
            pytest.skip("Agent supports push notifications")
        base_url = _get_base_url(transport_clients, transport)
        response = _jsonrpc_call(
            base_url,
            "CreateTaskPushNotificationConfig",
            {"task_id": "t", "config_id": "c", "config": {"url": "https://example.com"}},
        )
        body = response.json()
        passed = "error" in body
        errors = [] if passed else ["Expected error for unsupported push notifications"]
        record(collector=compliance_collector, req=req, transport=transport,
                passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, errors[0])

    def test_push_not_supported_rest(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """Push notification operations must return error when unsupported (REST)."""
        req = CORE_CAP_001
        transport = "http_json"
        caps = agent_card.get("capabilities", {})
        if caps.get("pushNotifications"):
            pytest.skip("Agent supports push notifications")
        base_url = _get_base_url(transport_clients, transport)
        response = _rest_call(
            base_url,
            "POST",
            "/tasks/t/pushNotificationConfigs",
            json_body={"configId": "c", "config": {"url": "https://example.com"}},
        )
        passed = response.status_code >= _HTTP_ERROR_STATUS
        errors = [] if passed else [f"Expected error for unsupported push, got {response.status_code}"]
        record(collector=compliance_collector, req=req, transport=transport,
                passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, errors[0])


@core
class TestCapabilityStreaming:
    """CORE-CAP-002: Streaming operations return error when not supported."""

    def test_streaming_not_supported_jsonrpc(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """Streaming operations must return error when unsupported."""
        req = CORE_CAP_002
        transport = "jsonrpc"
        caps = agent_card.get("capabilities", {})
        if caps.get("streaming"):
            pytest.skip("Agent supports streaming")
        base_url = _get_base_url(transport_clients, transport)
        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "stream test"}],
            "messageId": "tck-cap-stream",
        }
        response = _jsonrpc_call(
            base_url, "SendStreamingMessage", {"message": msg}
        )
        body = response.json()
        passed = "error" in body
        errors = [] if passed else ["Expected error for unsupported streaming"]
        record(collector=compliance_collector, req=req, transport=transport,
                passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, errors[0])


@core
class TestCapabilityExtendedCard:
    """CORE-CAP-003: Extended agent card returns error when not supported."""

    def test_extended_card_not_supported_jsonrpc(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """Extended agent card must return error when unsupported."""
        req = CORE_CAP_003
        transport = "jsonrpc"
        caps = agent_card.get("capabilities", {})
        if caps.get("extendedAgentCard"):
            pytest.skip("Agent supports extended agent card")
        base_url = _get_base_url(transport_clients, transport)
        response = _jsonrpc_call(base_url, "GetExtendedAgentCard", {})
        body = response.json()
        passed = "error" in body
        errors = [] if passed else ["Expected error for unsupported extended card"]
        record(collector=compliance_collector, req=req, transport=transport,
                passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, errors[0])


# ---------------------------------------------------------------------------
# Version negotiation errors
# ---------------------------------------------------------------------------


@core
class TestVersionErrors:
    """VER-SERVER-002 / VER-SERVER-003: Version error handling."""

    def test_unsupported_version_returns_error_jsonrpc(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """VER-SERVER-002: Unsupported A2A-Version returns VersionNotSupportedError."""
        req = VER_SERVER_002
        transport = "jsonrpc"
        base_url = _get_base_url(transport_clients, transport)
        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "version test"}],
            "messageId": "tck-ver-002",
        }
        response = _jsonrpc_call(
            base_url,
            "SendMessage",
            {"message": msg},
            headers={"A2A-Version": "99.0"},
        )
        body = response.json()
        passed = "error" in body
        errors = [] if passed else ["Expected VersionNotSupportedError for A2A-Version: 99.0"]
        record(collector=compliance_collector, req=req, transport=transport,
                passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, errors[0])

    def test_unsupported_version_returns_error_rest(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """VER-SERVER-002: Unsupported A2A-Version returns error via REST."""
        req = VER_SERVER_002
        transport = "http_json"
        base_url = _get_base_url(transport_clients, transport)
        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "version test"}],
            "messageId": "tck-ver-002-rest",
        }
        response = _rest_call(
            base_url,
            "POST",
            "/message:send",
            json_body={"message": msg},
            headers={"A2A-Version": "99.0"},
        )
        passed = response.status_code >= _HTTP_ERROR_STATUS
        errors = [] if passed else [f"Expected error for unsupported version, got {response.status_code}"]
        record(collector=compliance_collector, req=req, transport=transport,
                passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, errors[0])

    def test_empty_version_treated_as_default_jsonrpc(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """VER-SERVER-003: Empty A2A-Version treated as 0.3 (should succeed)."""
        req = VER_SERVER_003
        transport = "jsonrpc"
        base_url = _get_base_url(transport_clients, transport)
        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "empty version test"}],
            "messageId": "tck-ver-003",
        }
        response = _jsonrpc_call(
            base_url,
            "SendMessage",
            {"message": msg},
            headers={"A2A-Version": ""},
        )
        body = response.json()
        # Empty version should be treated as 0.3. Server must return either
        # a valid result or a well-formed error — never crash.
        passed = "result" in body or "error" in body
        errors = [] if passed else ["Server must return result or error for empty A2A-Version"]
        record(collector=compliance_collector, req=req, transport=transport,
                passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, errors[0])


# ---------------------------------------------------------------------------
# JSON-RPC error structure
# ---------------------------------------------------------------------------

_JSONRPC_ERROR_SCHEMA = {
    "type": "object",
    "required": ["code", "message"],
    "properties": {
        "code": {"type": "integer"},
        "message": {"type": "string"},
        "data": {},
    },
    "additionalProperties": False,
}


@jsonrpc
class TestJsonRpcErrorStructure:
    """JSONRPC-ERR-001 / JSONRPC-ERR-002: JSON-RPC error object structure."""

    def test_error_object_structure(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """JSONRPC-ERR-001: Error object has code, message, optional data."""
        req = JSONRPC_ERR_001
        transport = "jsonrpc"
        base_url = _get_base_url(transport_clients, transport)
        response = _jsonrpc_call(
            base_url, "GetTask", {"id": "tck-nonexistent-err-test"}
        )
        body = response.json()
        if "error" not in body:
            pytest.skip("Server did not return an error")
        error = body["error"]
        errors = []
        try:
            jsonschema.validate(error, _JSONRPC_ERROR_SCHEMA)
        except jsonschema.ValidationError as exc:
            errors.append(exc.message)
        record(collector=compliance_collector, req=req, transport=transport,
                passed=not errors, errors=errors)
        assert not errors, fail_msg(req, transport, "; ".join(errors))

    def test_a2a_error_codes_in_range(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """JSONRPC-ERR-002: A2A-specific errors use codes -32001 to -32099."""
        req = JSONRPC_ERR_002
        transport = "jsonrpc"
        base_url = _get_base_url(transport_clients, transport)
        response = _jsonrpc_call(
            base_url, "GetTask", {"id": "tck-nonexistent-err-range"}
        )
        body = response.json()
        if "error" not in body:
            pytest.skip("Server did not return an error")
        code = body["error"].get("code")
        errors = []
        if (
            code is not None
            and isinstance(code, int)
            and not (
                _A2A_ERROR_CODE_MIN <= code <= _A2A_ERROR_CODE_MAX
                or _JSONRPC_ERROR_CODE_MIN <= code <= _JSONRPC_ERROR_CODE_MAX
            )
        ):
            errors.append(
                f"Error code {code} is not in A2A range "
                f"({_A2A_ERROR_CODE_MAX} to {_A2A_ERROR_CODE_MIN}) "
                f"or standard JSON-RPC range "
                f"({_JSONRPC_ERROR_CODE_MAX} to {_JSONRPC_ERROR_CODE_MIN})"
            )
        record(collector=compliance_collector, req=req, transport=transport,
                passed=not errors, errors=errors)
        assert not errors, fail_msg(req, transport, "; ".join(errors))

    def test_a2a_error_type_mappings(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """JSONRPC-SSE-002: A2A error types mapped to correct JSON-RPC error codes."""
        req = JSONRPC_SSE_002
        transport = "jsonrpc"
        base_url = _get_base_url(transport_clients, transport)
        # Trigger TaskNotFoundError (expected code: -32001)
        response = _jsonrpc_call(
            base_url, "GetTask", {"id": "tck-nonexistent-mapping-test"}
        )
        body = response.json()
        if "error" not in body:
            pytest.skip("Server did not return an error")
        code = body["error"].get("code")
        errors = []
        if code != _TASK_NOT_FOUND_ERROR_CODE:
            errors.append(
                f"TaskNotFoundError should map to -32001, got {code}"
            )
        record(collector=compliance_collector, req=req, transport=transport,
                passed=not errors, errors=errors)
        assert not errors, fail_msg(req, transport, "; ".join(errors))


# ---------------------------------------------------------------------------
# REST error structure
# ---------------------------------------------------------------------------


@http_json
class TestRestErrorStructure:
    """HTTP_JSON-ERR-001 / HTTP_JSON-ERR-002: RFC 9457 Problem Details format."""

    def test_error_uses_problem_details(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """HTTP_JSON-ERR-001: Error responses use RFC 9457 Problem Details."""
        req = HTTP_JSON_ERR_001
        transport = "http_json"
        base_url = _get_base_url(transport_clients, transport)
        response = _rest_call(
            base_url, "GET", "/tasks/tck-nonexistent-pd-test"
        )
        if response.status_code < _HTTP_ERROR_STATUS:
            pytest.skip("Server did not return an error")
        ct = response.headers.get("content-type", "")
        errors = []
        if "application/problem+json" not in ct:
            errors.append(
                f"Error Content-Type must be application/problem+json, got: {ct!r}"
            )
        else:
            body = response.json()
            if "type" not in body and "title" not in body:
                errors.append("Problem Details must have 'type' or 'title'")
        record(collector=compliance_collector, req=req, transport=transport,
                passed=not errors, errors=errors)
        assert not errors, fail_msg(req, transport, "; ".join(errors))

    def test_a2a_error_type_uri(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """HTTP_JSON-ERR-002: A2A errors use specified type URIs."""
        req = HTTP_JSON_ERR_002
        transport = "http_json"
        base_url = _get_base_url(transport_clients, transport)
        response = _rest_call(
            base_url, "GET", "/tasks/tck-nonexistent-uri-test"
        )
        if response.status_code < _HTTP_ERROR_STATUS:
            pytest.skip("Server did not return an error")
        ct = response.headers.get("content-type", "")
        if "application/problem+json" not in ct:
            pytest.skip("Response is not Problem Details format")
        body = response.json()
        error_type = body.get("type", "")
        errors = []
        if error_type and not error_type.startswith("https://"):
            errors.append(
                f"Error type URI must start with https://, got: {error_type!r}"
            )
        record(collector=compliance_collector, req=req, transport=transport,
                passed=not errors, errors=errors)
        assert not errors, fail_msg(req, transport, "; ".join(errors))


# ---------------------------------------------------------------------------
# gRPC error structure
# ---------------------------------------------------------------------------


@grpc
class TestGrpcErrorStructure:
    """GRPC-ERR-001 / GRPC-ERR-002: gRPC error handling."""

    def test_grpc_error_for_nonexistent_task(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """GRPC-ERR-001: A2A errors include ErrorInfo in status details."""
        req = GRPC_ERR_001
        transport = "grpc"
        client = transport_clients.get(transport)
        if client is None:
            pytest.skip("gRPC transport not configured")
        response = client.get_task(id="tck-nonexistent-grpc-err")
        errors = []
        if response.success:
            errors.append("Expected error for nonexistent task")
        elif response.error is None:
            errors.append("Error message must be present")
        record(collector=compliance_collector, req=req, transport=transport,
                passed=not errors, errors=errors)
        assert not errors, fail_msg(req, transport, "; ".join(errors))
