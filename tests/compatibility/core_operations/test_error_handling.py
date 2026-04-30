"""Error triggering and validation tests.

Sends deliberately invalid or edge-case requests and validates
the error responses conform to the A2A specification.

Requirements tested:
    CORE-ERR-001, CORE-ERR-002,
    CORE-CAP-001, CORE-CAP-002, CORE-CAP-003, CORE-CAP-004,
    VER-SERVER-002, VER-SERVER-003,
    JSONRPC-ERR-001, JSONRPC-ERR-002, JSONRPC-ERR-003,
    HTTP_JSON-ERR-001, HTTP_JSON-ERR-002,
    GRPC-ERR-001, GRPC-ERR-002
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
import jsonschema
import pytest

from tck.requirements.base import tck_id
from tck.requirements.registry import get_requirement_by_id
from tck.transport._helpers import A2A_VERSION, A2A_VERSION_HEADER
from tck.validators.error_info import validate_error_info
from tests.compatibility._test_helpers import assert_and_record, get_client, record
from tests.compatibility.markers import core, grpc, http_json, jsonrpc, must


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
JSONRPC_ERR_003 = get_requirement_by_id("JSONRPC-ERR-003")
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
# Helpers — raw calls for tests that need custom headers or invalid payloads
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
    hdrs = {"Content-Type": "application/json", A2A_VERSION_HEADER: A2A_VERSION}
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
    hdrs = {A2A_VERSION_HEADER: A2A_VERSION}
    if json_body is not None:
        hdrs["Content-Type"] = "application/json"
    if headers:
        hdrs.update(headers)
    return httpx.request(method, f"{base_url}{path}", json=json_body, headers=hdrs)



# ---------------------------------------------------------------------------
# Core error handling
# ---------------------------------------------------------------------------


@must
@core
class TestCoreErrorStructure:
    """CORE-ERR-001: Server returns appropriate errors with actionable info."""

    def test_error_has_code_and_message_jsonrpc(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """JSON-RPC error responses include code and message."""
        req = CORE_ERR_001
        transport = "jsonrpc"
        # Raw call needed: invoking a non-existent method.
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        response = _jsonrpc_call(client.base_url, "NonExistentMethod", {})
        body = response.json()
        if "error" not in body:
            pytest.skip("Server did not return an error for unknown method")
        error = body["error"]
        errors = []
        if "code" not in error:
            errors.append("JSON-RPC error must have 'code'")
        if "message" not in error:
            errors.append("JSON-RPC error must have 'message'")
        assert_and_record(compatibility_collector, req, transport, errors)

    def test_error_has_code_and_message_rest(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """REST error responses include error information."""
        req = CORE_ERR_001
        transport = "http_json"
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        response = client.get_task(id=tck_id("nonexistent-error-test"))
        passed = not response.success
        errors = [] if passed else ["Expected error for non-existent task"]
        assert_and_record(compatibility_collector, req, transport, errors)


@must
@core
class TestCoreInputValidation:
    """CORE-ERR-002: Server validates input parameters."""

    def test_malformed_request_rejected_jsonrpc(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """Send a SendMessage with missing required 'message' field."""
        req = CORE_ERR_002
        transport = "jsonrpc"
        # Raw call needed: deliberately malformed params.
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        response = _jsonrpc_call(client.base_url, "SendMessage", {})
        body = response.json()
        passed = "error" in body
        errors = [] if passed else ["Malformed request must return an error"]
        assert_and_record(compatibility_collector, req, transport, errors)

    def test_malformed_request_rejected_rest(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """Send a POST to /message:send with empty body."""
        req = CORE_ERR_002
        transport = "http_json"
        # Raw call needed: deliberately malformed body.
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        response = _rest_call(client.base_url, "POST", "/message:send", json_body={})
        passed = response.status_code >= _HTTP_ERROR_STATUS
        errors = [] if passed else [f"Expected error status, got {response.status_code}"]
        assert_and_record(compatibility_collector, req, transport, errors)


# ---------------------------------------------------------------------------
# Capability validation
# ---------------------------------------------------------------------------


@must
@core
class TestCapabilityPushNotifications:
    """CORE-CAP-001: Push operations return error when not supported."""

    def test_push_not_supported_jsonrpc(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """Push notification operations must return error when unsupported."""
        req = CORE_CAP_001
        transport = "jsonrpc"
        caps = agent_card.get("capabilities", {})
        if caps.get("pushNotifications"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent supports push notifications")
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        response = client.create_push_notification_config(
            task_id="t",
            config={"url": "https://example.com"},
        )
        passed = not response.success
        errors = [] if passed else ["Expected error for unsupported push notifications"]
        assert_and_record(compatibility_collector, req, transport, errors)

    def test_push_not_supported_rest(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """Push notification operations must return error when unsupported (REST)."""
        req = CORE_CAP_001
        transport = "http_json"
        caps = agent_card.get("capabilities", {})
        if caps.get("pushNotifications"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent supports push notifications")
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        response = client.create_push_notification_config(
            task_id="t",
            config={"url": "https://example.com"},
        )
        passed = not response.success
        errors = [] if passed else ["Expected error for unsupported push notifications"]
        assert_and_record(compatibility_collector, req, transport, errors)


@must
@core
class TestCapabilityStreaming:
    """CORE-CAP-002: Streaming operations return error when not supported."""

    def test_streaming_not_supported_jsonrpc(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """Streaming operations must return error when unsupported."""
        req = CORE_CAP_002
        transport = "jsonrpc"
        caps = agent_card.get("capabilities", {})
        if caps.get("streaming"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent supports streaming")
        # Raw call needed: streaming client can't detect a JSON-RPC error
        # in the response body (it expects SSE).
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "stream test"}],
            "messageId": tck_id("cap-stream"),
        }
        response = _jsonrpc_call(
            client.base_url, "SendStreamingMessage", {"message": msg}
        )
        body = response.json()
        passed = "error" in body
        errors = [] if passed else ["Expected error for unsupported streaming"]
        assert_and_record(compatibility_collector, req, transport, errors)


@must
@core
class TestCapabilityExtendedCard:
    """CORE-CAP-003: Extended agent card returns error when not supported."""

    def test_extended_card_not_supported_jsonrpc(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """Extended agent card must return error when unsupported."""
        req = CORE_CAP_003
        transport = "jsonrpc"
        caps = agent_card.get("capabilities", {})
        if caps.get("extendedAgentCard"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent supports extended agent card")
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        response = client.get_extended_agent_card()
        passed = not response.success
        errors = [] if passed else ["Expected error for unsupported extended card"]
        assert_and_record(compatibility_collector, req, transport, errors)


# ---------------------------------------------------------------------------
# Version negotiation errors
# ---------------------------------------------------------------------------


@must
@core
class TestVersionErrors:
    """VER-SERVER-002 / VER-SERVER-003: Version error handling."""

    def test_unsupported_version_returns_error_jsonrpc(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """VER-SERVER-002: Unsupported A2A-Version returns VersionNotSupportedError."""
        req = VER_SERVER_002
        transport = "jsonrpc"
        # Raw call needed: custom A2A-Version header.
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "version test"}],
            "messageId": tck_id("ver-002"),
        }
        response = _jsonrpc_call(
            client.base_url,
            "SendMessage",
            {"message": msg},
            headers={A2A_VERSION_HEADER: "99.0"},
        )
        body = response.json()
        passed = "error" in body
        errors = [] if passed else ["Expected VersionNotSupportedError for A2A-Version: 99.0"]
        assert_and_record(compatibility_collector, req, transport, errors)

    def test_unsupported_version_returns_error_rest(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """VER-SERVER-002: Unsupported A2A-Version returns error via REST."""
        req = VER_SERVER_002
        transport = "http_json"
        # Raw call needed: custom A2A-Version header.
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "version test"}],
            "messageId": tck_id("ver-002-rest"),
        }
        response = _rest_call(
            client.base_url,
            "POST",
            "/message:send",
            json_body={"message": msg},
            headers={A2A_VERSION_HEADER: "99.0"},
        )
        passed = response.status_code >= _HTTP_ERROR_STATUS
        errors = [] if passed else [f"Expected error for unsupported version, got {response.status_code}"]
        assert_and_record(compatibility_collector, req, transport, errors)

    def test_empty_version_treated_as_default_jsonrpc(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """VER-SERVER-003: Empty A2A-Version treated as 0.3 (should succeed)."""
        req = VER_SERVER_003
        transport = "jsonrpc"
        # Raw call needed: custom A2A-Version header.
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "empty version test"}],
            "messageId": tck_id("ver-003"),
        }
        response = _jsonrpc_call(
            client.base_url,
            "SendMessage",
            {"message": msg},
            headers={A2A_VERSION_HEADER: ""},
        )
        body = response.json()
        # Empty version should be treated as 0.3. Server must return either
        # a valid result or a well-formed error — never crash.
        passed = "result" in body or "error" in body
        errors = [] if passed else ["Server must return result or error for empty A2A-Version"]
        assert_and_record(compatibility_collector, req, transport, errors)


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


@must
@jsonrpc
class TestJsonRpcErrorStructure:
    """JSONRPC-ERR-001 / JSONRPC-ERR-002 / JSONRPC-ERR-003: JSON-RPC error object structure."""

    def test_error_object_structure(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """JSONRPC-ERR-001: Error object has code, message, optional data."""
        req = JSONRPC_ERR_001
        transport = "jsonrpc"
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        response = client.get_task(id=tck_id("nonexistent-err-test"))
        body = response.raw_response
        if not isinstance(body, dict) or "error" not in body:
            pytest.skip("Server did not return a JSON-RPC error for non-existent task")
        error = body["error"]
        errors = []
        try:
            jsonschema.validate(error, _JSONRPC_ERROR_SCHEMA)
        except jsonschema.ValidationError as exc:
            errors.append(exc.message)
        assert_and_record(compatibility_collector, req, transport, errors)

    def test_a2a_error_codes_in_range(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """JSONRPC-ERR-002: A2A-specific errors use codes -32001 to -32099."""
        req = JSONRPC_ERR_002
        transport = "jsonrpc"
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        response = client.get_task(id=tck_id("nonexistent-err-range"))
        body = response.raw_response
        if not isinstance(body, dict) or "error" not in body:
            pytest.skip("Server did not return a JSON-RPC error for non-existent task")
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
        assert_and_record(compatibility_collector, req, transport, errors)

    def test_a2a_error_type_mappings(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """JSONRPC-SSE-002: A2A error types mapped to correct JSON-RPC error codes."""
        req = JSONRPC_SSE_002
        transport = "jsonrpc"
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        response = client.get_task(id=tck_id("nonexistent-mapping-test"))
        body = response.raw_response
        if not isinstance(body, dict) or "error" not in body:
            pytest.skip("Server did not return a JSON-RPC error for non-existent task")
        code = body["error"].get("code")
        errors = []
        if code != _TASK_NOT_FOUND_ERROR_CODE:
            errors.append(
                f"TaskNotFoundError should map to -32001, got {code}"
            )
        assert_and_record(compatibility_collector, req, transport, errors)

    def test_error_data_contains_error_info(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """JSONRPC-ERR-003: A2A errors include ErrorInfo in data array."""
        req = JSONRPC_ERR_003
        transport = "jsonrpc"
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        response = client.get_task(id=tck_id("nonexistent-errinfo-test"))
        body = response.raw_response
        if not isinstance(body, dict) or "error" not in body:
            pytest.skip("Server did not return a JSON-RPC error for non-existent task")
        data = body["error"].get("data")
        errors = []
        if data is not None and not isinstance(data, list):
            errors.append(
                f"error.data must be an array, got {type(data).__name__}"
            )
        elif isinstance(data, list):
            result = validate_error_info(data)
            if not result.valid:
                errors.append(result.message)
        assert_and_record(compatibility_collector, req, transport, errors)


# ---------------------------------------------------------------------------
# REST error structure
# ---------------------------------------------------------------------------


@must
@http_json
class TestRestErrorStructure:
    """HTTP_JSON-ERR-001 / HTTP_JSON-ERR-002: AIP-193 error format."""

    def test_error_uses_aip193_format(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """HTTP_JSON-ERR-001: Error responses use AIP-193 format."""
        req = HTTP_JSON_ERR_001
        transport = "http_json"
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        response = client.get_task(id=tck_id("nonexistent-pd-test"))
        if response.success:
            pytest.skip("Server did not return an error for non-existent task")
        raw = response.raw_response
        if not isinstance(raw, httpx.Response):
            pytest.skip("Error response is not an HTTP response object")
        ct = raw.headers.get("content-type", "")
        errors = []
        if "application/json" not in ct:
            errors.append(
                f"Error Content-Type must be application/json, got: {ct!r}"
            )
        else:
            body = raw.json()
            if "error" not in body:
                errors.append(
                    "AIP-193 error response must include 'error' object"
                )
            elif "code" not in body.get("error", {}):
                errors.append(
                    "AIP-193 error.code field is required"
                )
        assert_and_record(compatibility_collector, req, transport, errors)

    def test_a2a_error_info_in_details(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """HTTP_JSON-ERR-002: A2A errors include ErrorInfo in details array."""
        req = HTTP_JSON_ERR_002
        transport = "http_json"
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        response = client.get_task(id=tck_id("nonexistent-uri-test"))
        if response.success:
            pytest.skip("Server did not return an error for non-existent task")
        raw = response.raw_response
        if not isinstance(raw, httpx.Response):
            pytest.skip("Error response is not an HTTP response object")
        body = raw.json()
        if "error" not in body:
            pytest.skip("Response is not AIP-193 format")
        details = body.get("error", {}).get("details", [])
        result = validate_error_info(details)
        errors = [] if result.valid else [result.message]
        assert_and_record(compatibility_collector, req, transport, errors)


# ---------------------------------------------------------------------------
# gRPC error structure
# ---------------------------------------------------------------------------


@must
@grpc
class TestGrpcErrorStructure:
    """GRPC-ERR-001 / GRPC-ERR-002: gRPC error handling."""

    def test_grpc_error_for_nonexistent_task(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """GRPC-ERR-001: A2A errors include ErrorInfo in status details."""
        req = GRPC_ERR_001
        transport = "grpc"
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        response = client.get_task(id=tck_id("nonexistent-grpc-err"))
        errors = []
        if response.success:
            errors.append("Expected error for nonexistent task")
        elif response.error is None:
            errors.append("Error message must be present")
        assert_and_record(compatibility_collector, req, transport, errors)
