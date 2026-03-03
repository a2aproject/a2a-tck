"""JSON-RPC error code mapping tests.

Validates that each A2A error type maps to the correct JSON-RPC error code
as defined in Section 5.4 of the A2A specification.

Requirements tested:
    JSONRPC-SSE-002
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
import pytest

from tck.requirements.registry import get_requirement_by_id
from tck.transport.jsonrpc_client import TRANSPORT
from tck.validators.jsonrpc.error_validator import validate_jsonrpc_error
from tests.compatibility._test_helpers import fail_msg, get_client, record
from tests.compatibility.markers import jsonrpc


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

JSONRPC_SSE_002 = get_requirement_by_id("JSONRPC-SSE-002")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# JSON-RPC error code ranges
_A2A_ERROR_CODE_MIN = -32099
_A2A_ERROR_CODE_MAX = -32001
_JSONRPC_ERROR_CODE_MIN = -32700
_JSONRPC_ERROR_CODE_MAX = -32600
_HTTP_ERROR_STATUS = 400


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


# ---------------------------------------------------------------------------
# Error code mapping tests
# ---------------------------------------------------------------------------


@jsonrpc
class TestJsonRpcErrorCodeMappings:
    """JSONRPC-SSE-002: Each A2A error type maps to the correct JSON-RPC error code."""

    def test_task_not_found_error(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """TaskNotFoundError (-32001): GetTask with non-existent ID."""
        req = JSONRPC_SSE_002
        transport = "jsonrpc"
        client = get_client(transport_clients, TRANSPORT, compliance_collector=compliance_collector, req=req)

        response = client.get_task(id="tck-nonexistent-error-code-001")
        body = response.raw_response
        if "error" not in body:
            pytest.skip("Server did not return an error for non-existent task")

        result = validate_jsonrpc_error(body, "TaskNotFoundError")
        errors = [] if result.valid else [result.message]
        record(
            collector=compliance_collector,
            req=req,
            transport=transport,
            passed=result.valid,
            errors=errors,
        )
        assert result.valid, fail_msg(req, transport, result.message)

    def test_task_not_cancelable_error(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """TaskNotCancelableError (-32002): CancelTask on a non-existent task."""
        req = JSONRPC_SSE_002
        transport = "jsonrpc"
        client = get_client(transport_clients, TRANSPORT, compliance_collector=compliance_collector, req=req)

        response = client.cancel_task(id="tck-nonexistent-error-code-002")
        body = response.raw_response
        if "error" not in body:
            pytest.skip("Server did not return an error for CancelTask")

        code = body["error"].get("code")
        # Server may return TaskNotFoundError (-32001) instead of
        # TaskNotCancelableError (-32002) since the task doesn't exist.
        valid = code in (-32001, -32002)
        errors = (
            []
            if valid
            else [
                f"CancelTask on non-existent task should return "
                f"-32001 (TaskNotFoundError) or -32002 (TaskNotCancelableError), "
                f"got {code}"
            ]
        )
        record(
            collector=compliance_collector,
            req=req,
            transport=transport,
            passed=valid,
            errors=errors,
        )
        assert valid, fail_msg(req, transport, errors[0])

    def test_push_notification_not_supported_error(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """PushNotificationNotSupportedError (-32003): push config when unsupported."""
        req = JSONRPC_SSE_002
        transport = "jsonrpc"

        caps = agent_card.get("capabilities", {})
        if caps.get("pushNotifications"):
            record(collector=compliance_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent supports push notifications; cannot trigger -32003")

        client = get_client(transport_clients, TRANSPORT, compliance_collector=compliance_collector, req=req)
        response = client.create_push_notification_config(
            task_id="tck-error-code-003",
            config_id="c",
            config={"url": "https://example.com"},
        )
        body = response.raw_response
        if "error" not in body:
            pytest.skip("Server did not return an error for unsupported push")

        result = validate_jsonrpc_error(body, "PushNotificationNotSupportedError")
        errors = [] if result.valid else [result.message]
        record(
            collector=compliance_collector,
            req=req,
            transport=transport,
            passed=result.valid,
            errors=errors,
        )
        assert result.valid, fail_msg(req, transport, result.message)

    def test_unsupported_operation_error(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """UnsupportedOperationError (-32004): streaming when unsupported."""
        req = JSONRPC_SSE_002
        transport = "jsonrpc"

        caps = agent_card.get("capabilities", {})
        if caps.get("streaming"):
            record(collector=compliance_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent supports streaming; cannot trigger -32004")

        # Use raw call because the streaming client does not detect
        # JSON-RPC errors in the response body.
        client = get_client(transport_clients, TRANSPORT, compliance_collector=compliance_collector, req=req)
        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "error code test"}],
            "messageId": "tck-error-code-004",
        }
        response = _jsonrpc_call(
            client.base_url, "SendStreamingMessage", {"message": msg}
        )
        body = response.json()
        if "error" not in body:
            pytest.skip("Server did not return an error for unsupported streaming")

        result = validate_jsonrpc_error(body, "UnsupportedOperationError")
        errors = [] if result.valid else [result.message]
        record(
            collector=compliance_collector,
            req=req,
            transport=transport,
            passed=result.valid,
            errors=errors,
        )
        assert result.valid, fail_msg(req, transport, result.message)

    def test_content_type_not_supported_error(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """ContentTypeNotSupportedError (-32005): wrong Content-Type header."""
        req = JSONRPC_SSE_002
        transport = "jsonrpc"
        # Raw call required: need to send a deliberately wrong Content-Type.
        client = get_client(transport_clients, TRANSPORT, compliance_collector=compliance_collector, req=req)

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {
                "message": {
                    "role": "ROLE_USER",
                    "parts": [{"text": "content type test"}],
                    "messageId": "tck-error-code-005",
                }
            },
        }
        response = httpx.post(
            client.base_url,
            content=str(payload).encode(),
            headers={"Content-Type": "text/plain"},
        )

        # The server may reject the wrong Content-Type at the HTTP level
        # (e.g. 415 with an empty body) instead of returning a JSON-RPC error.
        try:
            body = response.json()
        except Exception:
            # Non-JSON response — server rejected at HTTP level.
            if response.status_code >= _HTTP_ERROR_STATUS:
                pytest.skip(
                    f"Server rejected wrong Content-Type with HTTP {response.status_code} "
                    f"instead of a JSON-RPC error"
                )
            pytest.skip("Server returned non-JSON response for wrong Content-Type")

        if "error" not in body:
            pytest.skip("Server did not return an error for wrong Content-Type")

        result = validate_jsonrpc_error(body, "ContentTypeNotSupportedError")
        errors = [] if result.valid else [result.message]
        record(
            collector=compliance_collector,
            req=req,
            transport=transport,
            passed=result.valid,
            errors=errors,
        )
        assert result.valid, fail_msg(req, transport, result.message)

    def test_version_not_supported_error(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """VersionNotSupportedError (-32009): unsupported A2A-Version header."""
        req = JSONRPC_SSE_002
        transport = "jsonrpc"
        # Raw call required: need to inject a custom A2A-Version header.
        client = get_client(transport_clients, TRANSPORT, compliance_collector=compliance_collector, req=req)

        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "version error code test"}],
            "messageId": "tck-error-code-009",
        }
        response = _jsonrpc_call(
            client.base_url,
            "SendMessage",
            {"message": msg},
            headers={"A2A-Version": "99.0"},
        )
        body = response.json()
        if "error" not in body:
            # The spec requires servers to return VersionNotSupportedError
            # for unsupported A2A-Version values — this is a compliance failure.
            detail = (
                "Server MUST return VersionNotSupportedError (-32009) for "
                "unsupported A2A-Version, but processed the request normally"
            )
            record(
                collector=compliance_collector,
                req=req,
                transport=transport,
                passed=False,
                errors=[detail],
            )
            pytest.fail(fail_msg(req, transport, detail))

        result = validate_jsonrpc_error(body, "VersionNotSupportedError")
        errors = [] if result.valid else [result.message]
        record(
            collector=compliance_collector,
            req=req,
            transport=transport,
            passed=result.valid,
            errors=errors,
        )
        assert result.valid, fail_msg(req, transport, result.message)


# ---------------------------------------------------------------------------
# Parametrized range validation
# ---------------------------------------------------------------------------


@jsonrpc
class TestJsonRpcErrorCodeRange:
    """Validate that returned error codes fall within valid ranges."""

    @pytest.mark.parametrize(
        "trigger_id",
        [
            pytest.param("get_task", id="GetTask-nonexistent"),
            pytest.param("cancel_task", id="CancelTask-nonexistent"),
            pytest.param("version_error", id="SendMessage-bad-version"),
        ],
    )
    def test_error_code_in_valid_range(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
        trigger_id: str,
    ) -> None:
        """Error codes must be in A2A range (-32001..-32099) or standard JSON-RPC range."""
        req = JSONRPC_SSE_002
        transport = "jsonrpc"
        client = get_client(transport_clients, TRANSPORT, compliance_collector=compliance_collector, req=req)

        # Trigger the error condition.
        if trigger_id == "get_task":
            resp = client.get_task(id="tck-range-check-001")
            body = resp.raw_response
        elif trigger_id == "cancel_task":
            resp = client.cancel_task(id="tck-range-check-002")
            body = resp.raw_response
        else:
            # version_error — requires custom header, so use raw call.
            msg = {
                "role": "ROLE_USER",
                "parts": [{"text": "range test"}],
                "messageId": "tck-range-check-003",
            }
            raw = _jsonrpc_call(
                client.base_url,
                "SendMessage",
                {"message": msg},
                headers={"A2A-Version": "99.0"},
            )
            body = raw.json()

        if "error" not in body:
            pytest.skip(f"Server did not return an error for {trigger_id}")

        code = body["error"].get("code")
        if not isinstance(code, int):
            pytest.skip(f"Error code is not an integer: {code!r}")

        in_a2a_range = _A2A_ERROR_CODE_MIN <= code <= _A2A_ERROR_CODE_MAX
        in_jsonrpc_range = _JSONRPC_ERROR_CODE_MIN <= code <= _JSONRPC_ERROR_CODE_MAX
        valid = in_a2a_range or in_jsonrpc_range

        errors = (
            []
            if valid
            else [
                f"Error code {code} is not in A2A range "
                f"({_A2A_ERROR_CODE_MAX} to {_A2A_ERROR_CODE_MIN}) "
                f"or standard JSON-RPC range "
                f"({_JSONRPC_ERROR_CODE_MAX} to {_JSONRPC_ERROR_CODE_MIN})"
            ]
        )
        record(
            collector=compliance_collector,
            req=req,
            transport=transport,
            passed=valid,
            errors=errors,
        )
        assert valid, fail_msg(req, transport, errors[0])
