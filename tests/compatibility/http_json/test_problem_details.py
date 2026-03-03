"""HTTP+JSON Problem Details validation tests.

Validates that HTTP+JSON error responses conform to RFC 9457 Problem Details
format as required by Section 11.6 of the A2A specification.

Requirements tested:
    HTTP_JSON-ERR-001, HTTP_JSON-ERR-002
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import A2A_ERROR_TYPE_URIS, TASK_NOT_FOUND_ERROR
from tck.requirements.registry import get_requirement_by_id
from tck.transport.http_json_client import TRANSPORT
from tck.validators.http_json.error_validator import ProblemDetails
from tests.compatibility._test_helpers import fail_msg, get_client, record
from tests.compatibility.markers import http_json


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
    response = client.get_task(id="tck-nonexistent-pd-001")
    if response.success:
        pytest.skip("Server did not return an error for non-existent task")
    return response


def _get_problem_body(response: Any) -> dict[str, Any] | None:
    """Extract the Problem Details body from a response, if applicable.

    Returns None (and skips the test) when the response Content-Type is not
    ``application/problem+json``.
    """
    headers = response.headers or {}
    ct = ""
    for key, value in headers.items():
        if key.lower() == "content-type":
            ct = value
            break
    if "application/problem+json" not in ct.lower():
        pytest.skip("Response is not Problem Details format")
    body = response.raw_response
    if not isinstance(body, dict):
        pytest.skip("Response body is not a JSON object")
    return body


# ---------------------------------------------------------------------------
# Problem Details format tests (HTTP_JSON-ERR-001)
# ---------------------------------------------------------------------------


@http_json
class TestProblemDetailsFormat:
    """HTTP_JSON-ERR-001: Error responses use RFC 9457 Problem Details format."""

    def test_error_content_type(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """Error response has Content-Type: application/problem+json."""
        req = HTTP_JSON_ERR_001
        client = get_client(transport_clients, TRANSPORT)
        response = _get_error_response(client)

        headers = response.headers or {}
        ct = ""
        for key, value in headers.items():
            if key.lower() == "content-type":
                ct = value
                break

        valid = "application/problem+json" in ct.lower()
        errors = (
            []
            if valid
            else [
                f"Error Content-Type must be application/problem+json, got: {ct!r}"
            ]
        )
        record(
            collector=compliance_collector,
            req=req,
            transport=TRANSPORT,
            passed=valid,
            errors=errors,
        )
        assert valid, fail_msg(req, TRANSPORT, errors[0])

    def test_required_fields_present(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """Body contains required fields: type, title, status."""
        req = HTTP_JSON_ERR_001
        client = get_client(transport_clients, TRANSPORT)
        response = _get_error_response(client)
        body = _get_problem_body(response)

        errors: list[str] = []
        try:
            ProblemDetails.from_dict(body)
        except ValueError as exc:
            errors.append(str(exc))

        record(
            collector=compliance_collector,
            req=req,
            transport=TRANSPORT,
            passed=not errors,
            errors=errors,
        )
        assert not errors, fail_msg(req, TRANSPORT, "; ".join(errors))

    def test_status_field_matches_http_status(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """The ``status`` field value equals the HTTP response status code."""
        req = HTTP_JSON_ERR_001
        client = get_client(transport_clients, TRANSPORT)
        response = _get_error_response(client)
        body = _get_problem_body(response)

        try:
            pd = ProblemDetails.from_dict(body)
        except ValueError:
            pytest.skip("Problem Details missing required fields")

        valid = pd.status == response.status_code
        errors = (
            []
            if valid
            else [
                f"Problem Details status ({pd.status}) does not match "
                f"HTTP status code ({response.status_code})"
            ]
        )
        record(
            collector=compliance_collector,
            req=req,
            transport=TRANSPORT,
            passed=valid,
            errors=errors,
        )
        assert valid, fail_msg(req, TRANSPORT, errors[0])

    def test_optional_fields_valid(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """If ``detail`` or ``instance`` are present, they must be strings."""
        req = HTTP_JSON_ERR_001
        client = get_client(transport_clients, TRANSPORT)
        response = _get_error_response(client)
        body = _get_problem_body(response)

        errors: list[str] = []
        if "detail" in body and not isinstance(body["detail"], str):
            errors.append(
                f"'detail' field must be a string, got {type(body['detail']).__name__}"
            )
        if "instance" in body and not isinstance(body["instance"], str):
            errors.append(
                f"'instance' field must be a string, got {type(body['instance']).__name__}"
            )

        record(
            collector=compliance_collector,
            req=req,
            transport=TRANSPORT,
            passed=not errors,
            errors=errors,
        )
        assert not errors, fail_msg(req, TRANSPORT, "; ".join(errors))


# ---------------------------------------------------------------------------
# Problem Details type URI tests (HTTP_JSON-ERR-002)
# ---------------------------------------------------------------------------


@http_json
class TestProblemDetailsTypeUri:
    """HTTP_JSON-ERR-002: A2A errors use specified type URIs."""

    def test_type_is_a2a_error_uri(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """The ``type`` field matches one of the spec-defined A2A error URIs."""
        req = HTTP_JSON_ERR_002
        client = get_client(transport_clients, TRANSPORT)
        response = _get_error_response(client)
        body = _get_problem_body(response)

        error_type = body.get("type", "")
        valid = error_type in A2A_ERROR_TYPE_URIS
        errors = (
            []
            if valid
            else [
                f"type URI {error_type!r} is not a recognised A2A error URI"
            ]
        )
        record(
            collector=compliance_collector,
            req=req,
            transport=TRANSPORT,
            passed=valid,
            errors=errors,
        )
        assert valid, fail_msg(req, TRANSPORT, errors[0])

    def test_type_uri_matches_error_condition(
        self,
        transport_clients: dict[str, BaseTransportClient],
        compliance_collector: Any,
    ) -> None:
        """For a TaskNotFound trigger, type must be the task-not-found URI."""
        req = HTTP_JSON_ERR_002
        client = get_client(transport_clients, TRANSPORT)
        response = _get_error_response(client)
        body = _get_problem_body(response)

        expected_uri = TASK_NOT_FOUND_ERROR.type_uri
        error_type = body.get("type", "")
        valid = error_type == expected_uri
        errors = (
            []
            if valid
            else [
                f"TaskNotFoundError should have type {expected_uri!r}, "
                f"got {error_type!r}"
            ]
        )
        record(
            collector=compliance_collector,
            req=req,
            transport=TRANSPORT,
            passed=valid,
            errors=errors,
        )
        assert valid, fail_msg(req, TRANSPORT, errors[0])
