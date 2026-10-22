"""HTTP+JSON error validator for A2A protocol responses.

This module provides validation of HTTP+JSON error responses according to
Section 11 of the A2A specification, using the AIP-193 error format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from google.protobuf.json_format import ParseDict, ParseError
from google.protobuf.wrappers_pb2 import Int32Value
from google.rpc.code_pb2 import Code

from tck.requirements.base import ERROR_BINDINGS
from tck.validators.error_info import validate_error_details, validate_error_info


# HTTP status code mappings for A2A errors, derived from central ErrorBinding definitions.
HTTP_JSON_ERROR_STATUS: dict[str, int] = {
    name: binding.http_status
    for name, binding in ERROR_BINDINGS.items()
    if binding.http_status != 0
}

# Reverse mapping from status codes to possible error names
# Note: Multiple errors can map to the same status code
STATUS_TO_ERRORS: dict[int, list[str]] = {}
for _name, _status in HTTP_JSON_ERROR_STATUS.items():
    STATUS_TO_ERRORS.setdefault(_status, []).append(_name)


def _protojson_int32(value: Any, field_name: str) -> int:
    """Use ProtoJSON's scalar grammar without truncating fractional values."""
    try:
        return ParseDict(value, Int32Value()).value
    except (ParseError, TypeError, ValueError) as error:
        raise ValueError(f"Error {field_name} must be a ProtoJSON int32 value") from error


def _grpc_status_name(value: Any) -> str:
    """The optional AIP-193 status is a google.rpc.Code enum, not a string field."""
    if value is None:
        return ""
    names = Code.keys()
    if isinstance(value, str) and value in names:
        return value
    try:
        return Code.Name(_protojson_int32(value, "status"))
    except ValueError as error:
        raise ValueError("Error status must be a google.rpc.Code value") from error


@dataclass
class AIP193Error:
    """AIP-193 error representation.

    This dataclass represents the error format specified in AIP-193
    (https://google.aip.dev/193#http11json-representation).

    Attributes:
        code: The HTTP status code.
        status: The gRPC status string (e.g., "NOT_FOUND").
        message: A human-readable error message.
        details: An array of google.protobuf.Any messages in ProtoJSON format.
    """

    code: int
    status: str = ""
    message: str = ""
    details: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AIP193Error:
        """Create an AIP193Error instance from a response body dictionary.

        Expects the AIP-193 format: ``{"error": {"code": ..., "status": ..., ...}}``.

        Raises:
            ValueError: If the required structure is missing.
        """
        if not isinstance(data, dict) or "error" not in data:
            raise ValueError("Response body missing required 'error' field")
        error = data["error"]
        if not isinstance(error, dict):
            raise ValueError(f"'error' field must be an object, got {type(error).__name__}")
        if "code" not in error:
            raise ValueError("Error object missing required 'code' field")

        # AIP-193's int32 uses ProtoJSON's accepted numeric/string forms,
        # including exponent notation. Use the official parser for numeric
        # conversion and bounds instead of imposing Python's scalar types.
        code = _protojson_int32(error["code"], "code")
        status = _grpc_status_name(error.get("status"))
        message = error.get("message")
        if message is None:
            message = ""
        elif not isinstance(message, str):
            raise ValueError("Error message must be a string")
        # ProtoJSON null denotes an unset optional/repeated field. JSON-RPC's
        # envelope data rule is separate and keeps its explicit array check.
        details = error.get("details")
        if details is None:
            details = []
        errors = validate_error_details(details)
        if errors:
            raise ValueError("; ".join(errors))
        return cls(
            code=code,
            status=status,
            message=message,
            details=details,
        )


@dataclass
class ErrorValidationResult:
    """Result of an HTTP+JSON error validation.

    Attributes:
        valid: True if the error response matches the expected error.
        expected_status: The expected HTTP status code.
        actual_status: The actual HTTP status code from the response.
        aip193_error: Parsed AIP-193 error, if present.
        message: A descriptive message about the validation result.
    """

    valid: bool
    expected_status: int
    actual_status: int | None
    aip193_error: AIP193Error | None = None
    message: str = ""


@runtime_checkable
class HTTPResponse(Protocol):
    """Protocol for HTTP response objects."""

    @property
    def status_code(self) -> int:
        """The HTTP status code."""
        ...

    @property
    def headers(self) -> dict[str, str]:
        """The response headers."""
        ...

    def json(self) -> Any:
        """Parse the response body as JSON."""
        ...


def validate_http_json_error(
    response: HTTPResponse | dict[str, Any], expected_error: str
) -> ErrorValidationResult:
    """Validate an HTTP+JSON error response against an expected error type.

    Args:
        response: Either an HTTP response object (with status_code, headers, json())
                  or a dict with 'status_code', 'headers', and 'body' keys.
        expected_error: The expected error name (e.g., "TaskNotFoundError").

    Returns:
        An ErrorValidationResult with validation status and details.
    """
    if expected_error not in HTTP_JSON_ERROR_STATUS:
        return ErrorValidationResult(
            valid=False, expected_status=0, actual_status=None,
            message=f"Unknown error type: {expected_error}",
        )
    expected_status = HTTP_JSON_ERROR_STATUS[expected_error]
    if isinstance(response, dict):
        actual_status, body = response.get("status_code"), response.get("body")
    elif isinstance(response, HTTPResponse):
        actual_status, body = response.status_code, response
    else:
        return ErrorValidationResult(
            valid=False, expected_status=expected_status, actual_status=None,
            message="Response does not contain a status code",
        )

    result = ErrorValidationResult(False, expected_status, None)
    if not isinstance(actual_status, int) or isinstance(actual_status, bool):
        result.message = "Response status code must be an integer"
        return result
    result.actual_status = actual_status
    if actual_status != expected_status:
        possible_errors = STATUS_TO_ERRORS.get(actual_status, [])
        result.message = (
            f"Status code mismatch: expected {expected_error} ({expected_status}), "
            f"got {actual_status} (could be: {', '.join(possible_errors)})"
        )
        return result

    try:
        parsed = _parse_error_body(body)
    except ValueError as error:
        result.message = f"Invalid AIP-193 error: {error}"
        return result
    result.aip193_error = parsed
    if parsed.code != actual_status:
        result.message = "AIP-193 error.code must equal the HTTP status code"
        return result
    expected_grpc_status = ERROR_BINDINGS[expected_error].grpc_status
    if parsed.status and expected_grpc_status and parsed.status != expected_grpc_status:
        result.message = f"AIP-193 status does not match {expected_error}"
        return result
    reason = ERROR_BINDINGS[expected_error].reason
    if reason is not None:
        identity = validate_error_info(parsed.details, expected_reason=reason)
        if not identity.valid:
            result.message = identity.message
            return result
    result.valid = True
    result.message = f"HTTP error matches: {expected_error} ({expected_status})"
    return result


def _parse_error_body(body: Any) -> AIP193Error:
    """Normalize direct HTTP responses and the actual compatibility-probe wrapper."""
    if isinstance(body, HTTPResponse):
        body = body.json()
    if not isinstance(body, dict):
        raise ValueError("Response body must be an object")
    return AIP193Error.from_dict(body)


def _get_content_type(headers: dict[str, str]) -> str | None:
    """Get the Content-Type header value (case-insensitive)."""
    for key, value in headers.items():
        if key.lower() == "content-type":
            return value
    return None


def get_expected_status(error_name: str) -> int | None:
    """Get the expected HTTP status code for an error name."""
    return HTTP_JSON_ERROR_STATUS.get(error_name)


def get_possible_errors(status_code: int) -> list[str]:
    """Get the possible error names for a given HTTP status code."""
    return STATUS_TO_ERRORS.get(status_code, [])
