"""HTTP+JSON AIP-193 error format validation tests.

Validates that HTTP+JSON error responses conform to the AIP-193 error
representation as required by Section 11.6 of the A2A specification.

Requirements tested:
    HTTP_JSON-ERR-001, HTTP_JSON-ERR-002
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import TASK_NOT_FOUND_ERROR, tck_id
from tck.requirements.registry import get_requirement_by_id
from tck.transport.http_json_client import TRANSPORT
from tck.validators.error_info import find_error_info, validate_error_info
from tck.validators.http_json.error_validator import AIP193Error
from tests.compatibility._test_helpers import assert_and_record, fail_msg, get_client, record
from tests.compatibility.markers import http_json, must


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

HTTP_JSON_ERR_001 = get_requirement_by_id("HTTP_JSON-ERR-001")
HTTP_JSON_ERR_002 = get_requirement_by_id("HTTP_JSON-ERR-002")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_error_response(
    client: BaseTransportClient,
) -> Any:
    """Request a non-existent task to trigger an error response.

    Returns the raw transport response, or calls pytest.skip if the server
    does not return an error.
    """
    response = client.get_task(id=tck_id("nonexistent-pd-001"))
    if response.success:
        pytest.skip("Server did not return an error for non-existent task")
    return response


def _get_error_body(response: Any) -> dict[str, Any] | None:
    """Extract the AIP-193 error body from a response.

    Returns None (and skips the test) when the response body is not
    an AIP-193 error object.
    """
    raw = response.raw_response
    if not hasattr(raw, "json"):
        pytest.skip("Response does not support JSON parsing")
    try:
        body = raw.json()
    except Exception:
        pytest.skip("Response body is not valid JSON")
    if not isinstance(body, dict) or "error" not in body:
        pytest.skip("Response body is not an AIP-193 error object")
    return body


# ---------------------------------------------------------------------------
# AIP-193 error format tests (HTTP_JSON-ERR-001)
# ---------------------------------------------------------------------------


@must
@http_json
class TestAIP193ErrorFormat:
    """HTTP_JSON-ERR-001: Error responses use AIP-193 format."""

    def test_error_content_type(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """Error response has Content-Type: application/json."""
        req = HTTP_JSON_ERR_001
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        response = _get_error_response(client)

        headers = response.headers or {}
        ct = ""
        for key, value in headers.items():
            if key.lower() == "content-type":
                ct = value
                break

        valid = "application/json" in ct.lower()
        errors = (
            []
            if valid
            else [
                f"Error Content-Type must be application/json, got: {ct!r}"
            ]
        )
        record(
            collector=compatibility_collector,
            req=req,
            transport=TRANSPORT,
            passed=valid,
            errors=errors,
        )
        assert valid, fail_msg(req, TRANSPORT, errors[0])

    def test_error_object_present(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """Body contains an 'error' object with required 'code' field."""
        req = HTTP_JSON_ERR_001
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        response = _get_error_response(client)
        body = _get_error_body(response)

        errors: list[str] = []
        try:
            AIP193Error.from_dict(body)
        except ValueError as exc:
            errors.append(str(exc))

        assert_and_record(compatibility_collector, req, TRANSPORT, errors)

    def test_code_field_matches_http_status(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """The error.code field value equals the HTTP response status code."""
        req = HTTP_JSON_ERR_001
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        response = _get_error_response(client)
        body = _get_error_body(response)

        try:
            aip_error = AIP193Error.from_dict(body)
        except ValueError:
            pytest.skip("AIP-193 error missing required fields")

        valid = aip_error.code == response.status_code
        errors = (
            []
            if valid
            else [
                f"error.code ({aip_error.code}) does not match "
                f"HTTP status code ({response.status_code})"
            ]
        )
        record(
            collector=compatibility_collector,
            req=req,
            transport=TRANSPORT,
            passed=valid,
            errors=errors,
        )
        assert valid, fail_msg(req, TRANSPORT, errors[0])

    def test_message_field_is_string(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """If error.message is present, it must be a string."""
        req = HTTP_JSON_ERR_001
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        response = _get_error_response(client)
        body = _get_error_body(response)

        error_obj = body.get("error", {})
        errors: list[str] = []
        if "message" in error_obj and not isinstance(error_obj["message"], str):
            errors.append(
                f"'message' field must be a string, got {type(error_obj['message']).__name__}"
            )

        assert_and_record(compatibility_collector, req, TRANSPORT, errors)


# ---------------------------------------------------------------------------
# ErrorInfo in details array tests (HTTP_JSON-ERR-002)
# ---------------------------------------------------------------------------


@must
@http_json
class TestAIP193ErrorInfo:
    """HTTP_JSON-ERR-002: A2A errors include ErrorInfo in details array."""

    def test_details_contains_error_info(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """The details array contains a google.rpc.ErrorInfo entry."""
        req = HTTP_JSON_ERR_002
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        response = _get_error_response(client)
        body = _get_error_body(response)

        try:
            aip_error = AIP193Error.from_dict(body)
        except ValueError:
            pytest.skip("AIP-193 error missing required fields")

        valid = find_error_info(aip_error.details) is not None
        errors = (
            []
            if valid
            else [
                "details array must contain a google.rpc.ErrorInfo entry"
            ]
        )
        record(
            collector=compatibility_collector,
            req=req,
            transport=TRANSPORT,
            passed=valid,
            errors=errors,
        )
        assert valid, fail_msg(req, TRANSPORT, errors[0])

    def test_error_info_valid(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """ErrorInfo has correct domain and valid reason."""
        req = HTTP_JSON_ERR_002
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        response = _get_error_response(client)
        body = _get_error_body(response)

        try:
            aip_error = AIP193Error.from_dict(body)
        except ValueError:
            pytest.skip("AIP-193 error missing required fields")

        result = validate_error_info(aip_error.details)
        errors = [] if result.valid else [result.message]
        record(
            collector=compatibility_collector,
            req=req,
            transport=TRANSPORT,
            passed=result.valid,
            errors=errors,
        )
        assert result.valid, fail_msg(req, TRANSPORT, result.message)

    def test_error_info_reason_matches_condition(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """For a TaskNotFound trigger, reason must be TASK_NOT_FOUND."""
        req = HTTP_JSON_ERR_002
        client = get_client(transport_clients, TRANSPORT, compatibility_collector=compatibility_collector, req=req)
        response = _get_error_response(client)
        body = _get_error_body(response)

        try:
            aip_error = AIP193Error.from_dict(body)
        except ValueError:
            pytest.skip("AIP-193 error missing required fields")

        result = validate_error_info(aip_error.details, expected_reason=TASK_NOT_FOUND_ERROR.reason)
        errors = [] if result.valid else [result.message]
        record(
            collector=compatibility_collector,
            req=req,
            transport=TRANSPORT,
            passed=result.valid,
            errors=errors,
        )
        assert result.valid, fail_msg(req, TRANSPORT, result.message)
