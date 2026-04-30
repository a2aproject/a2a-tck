"""HTTP+JSON status code mapping tests.

Validates that each A2A error type maps to the correct HTTP status code
as defined in Section 5.4 of the A2A specification.

Requirements tested:
    HTTP_JSON-STATUS-001
"""

from __future__ import annotations

import json

from typing import TYPE_CHECKING, Any

import httpx
import pytest

from tck.requirements.base import SEND_MESSAGE_BINDING, tck_id
from tck.requirements.registry import get_requirement_by_id
from tck.transport._helpers import A2A_VERSION, A2A_VERSION_HEADER
from tck.transport.http_json_client import TRANSPORT
from tck.validators.http_json.error_validator import validate_http_json_error
from tests.compatibility._test_helpers import assert_and_record, fail_msg, get_client, record
from tests.compatibility.markers import http_json, must


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

HTTP_JSON_STATUS_001 = get_requirement_by_id("HTTP_JSON-STATUS-001")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HTTP_ERROR_MIN = 400
_HTTP_SUCCESS_MIN = 200
_HTTP_SUCCESS_MAX = 299


# ---------------------------------------------------------------------------
# Status code mapping tests
# ---------------------------------------------------------------------------


@must
@http_json
class TestHttpJsonStatusCodes:
    """HTTP_JSON-STATUS-001: A2A errors map to correct HTTP status codes."""

    def test_task_not_found_returns_404(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """TaskNotFoundError: GET /tasks/{nonexistent} returns 404."""
        req = HTTP_JSON_STATUS_001
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)

        response = client.get_task(id=tck_id("nonexistent-status-001"))
        if response.success:
            pytest.skip("Server did not return an error for non-existent task")

        result = validate_http_json_error(
            {"status_code": response.status_code, "headers": response.headers, "body": response.raw_response},
            "TaskNotFoundError",
        )
        errors = [] if result.valid else [result.message]
        assert_and_record(compatibility_collector, req, TRANSPORT, errors)

    def test_task_not_cancelable_returns_409(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """TaskNotCancelableError: POST /tasks/{id}:cancel on non-existent returns 409 (or 404)."""
        req = HTTP_JSON_STATUS_001
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)

        response = client.cancel_task(id=tck_id("nonexistent-status-002"))
        if response.success:
            pytest.skip("Server did not return an error for CancelTask")

        status = response.status_code
        # Server may return 404 (TaskNotFoundError) instead of 409
        # (TaskNotCancelableError) since the task doesn't exist.
        valid = status in (404, 409)
        errors = (
            []
            if valid
            else [
                f"CancelTask on non-existent task should return "
                f"404 (TaskNotFoundError) or 409 (TaskNotCancelableError), "
                f"got {status}"
            ]
        )
        assert_and_record(compatibility_collector, req, TRANSPORT, errors)

    def test_unsupported_operation_returns_400(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """UnsupportedOperationError: streaming when unsupported returns 400."""
        req = HTTP_JSON_STATUS_001

        caps = agent_card.get("capabilities", {})
        if caps.get("streaming"):
            record(collector=compatibility_collector, req=req, transport=TRANSPORT, passed=False, skipped=True)
            pytest.skip("Agent supports streaming; cannot trigger UnsupportedOperationError")

        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "status code test"}],
            "messageId": tck_id("status-unsupported-003"),
        }
        response = client.send_streaming_message(message=msg)
        if response.success:
            pytest.skip("Server did not return an error for unsupported streaming")

        result = validate_http_json_error(
            {"status_code": response.status_code, "headers": response.headers, "body": response.raw_response},
            "UnsupportedOperationError",
        )
        errors = [] if result.valid else [result.message]
        assert_and_record(compatibility_collector, req, TRANSPORT, errors)

    def test_content_type_not_supported_returns_415(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """ContentTypeNotSupportedError: wrong Content-Type returns 415."""
        req = HTTP_JSON_STATUS_001
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)

        # Send a request with a deliberately wrong Content-Type.
        response = httpx.post(
            f"{client.base_url}{SEND_MESSAGE_BINDING.http_json_path}",
            content=json.dumps({"message": {"role": "ROLE_USER", "parts": [{"text": "ct test"}], "messageId": tck_id("status-ct-004")}}).encode(),
            headers={"Content-Type": "text/plain", A2A_VERSION_HEADER: A2A_VERSION},
        )

        if response.status_code < _HTTP_ERROR_MIN:
            pytest.skip("Server accepted wrong Content-Type without error")

        result = validate_http_json_error(response, "ContentTypeNotSupportedError")
        errors = [] if result.valid else [result.message]
        assert_and_record(compatibility_collector, req, TRANSPORT, errors)

    def test_push_not_supported_returns_400(
        self,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """PushNotificationNotSupportedError: push config when unsupported returns 400."""
        req = HTTP_JSON_STATUS_001

        caps = agent_card.get("capabilities", {})
        if caps.get("pushNotifications"):
            record(collector=compatibility_collector, req=req, transport=TRANSPORT, passed=False, skipped=True)
            pytest.skip("Agent supports push notifications; cannot trigger error")

        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        response = client.create_push_notification_config(
            task_id=tck_id("status-push-005"),
            config={"url": "https://example.com"},
        )
        if response.success:
            pytest.skip("Server did not return an error for unsupported push")

        result = validate_http_json_error(
            {"status_code": response.status_code, "headers": response.headers, "body": response.raw_response},
            "PushNotificationNotSupportedError",
        )
        errors = [] if result.valid else [result.message]
        assert_and_record(compatibility_collector, req, TRANSPORT, errors)

    def test_version_not_supported_returns_400(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """VersionNotSupportedError: unsupported A2A-Version returns 400."""
        req = HTTP_JSON_STATUS_001
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)

        # Raw request needed to inject a custom A2A-Version header.
        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "version status test"}],
            "messageId": tck_id("status-ver-006"),
        }
        response = httpx.post(
            f"{client.base_url}{SEND_MESSAGE_BINDING.http_json_path}",
            json={"message": msg},
            headers={
                "Content-Type": "application/json",
                A2A_VERSION_HEADER: "99.0",
            },
        )

        if response.status_code < _HTTP_ERROR_MIN:
            detail = (
                "Server MUST return VersionNotSupportedError (400) for "
                "unsupported A2A-Version, but processed the request normally"
            )
            record(
                collector=compatibility_collector,
                req=req,
                transport=TRANSPORT,
                passed=False,
                errors=[detail],
            )
            pytest.fail(fail_msg(req, TRANSPORT, detail))

        result = validate_http_json_error(response, "VersionNotSupportedError")
        errors = [] if result.valid else [result.message]
        assert_and_record(compatibility_collector, req, TRANSPORT, errors)

    def test_success_returns_2xx(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """Successful operations return HTTP 2xx status code."""
        req = HTTP_JSON_STATUS_001
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)

        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "status code success test"}],
            "messageId": tck_id("status-success-007"),
        }
        response = client.send_message(message=msg)
        if not response.success:
            pytest.skip(f"SendMessage failed: {response.error}")

        status = response.status_code
        valid = _HTTP_SUCCESS_MIN <= status <= _HTTP_SUCCESS_MAX
        errors = (
            []
            if valid
            else [f"Successful SendMessage should return 2xx, got {status}"]
        )
        assert_and_record(compatibility_collector, req, TRANSPORT, errors)
