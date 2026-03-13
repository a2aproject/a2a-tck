"""HTTP+JSON error validator for A2A protocol responses.

This module provides validation of HTTP+JSON error responses according to
Section 11 of the A2A specification, using the AIP-193 error format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from tck.requirements.base import ERROR_BINDINGS


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
        if "error" not in data:
            raise ValueError("Response body missing required 'error' field")
        error = data["error"]
        if not isinstance(error, dict):
            raise ValueError(f"'error' field must be an object, got {type(error).__name__}")
        if "code" not in error:
            raise ValueError("Error object missing required 'code' field")

        return cls(
            code=int(error["code"]),
            status=str(error.get("status", "")),
            message=str(error.get("message", "")),
            details=error.get("details", []),
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
    # Get the expected status code
    if expected_error not in HTTP_JSON_ERROR_STATUS:
        return ErrorValidationResult(
            valid=False,
            expected_status=0,
            actual_status=None,
            aip193_error=None,
            message=f"Unknown error type: {expected_error}. "
            f"Valid types: {', '.join(sorted(HTTP_JSON_ERROR_STATUS.keys()))}",
        )

    expected_status = HTTP_JSON_ERROR_STATUS[expected_error]

    # Extract status code and body from response
    try:
        if isinstance(response, dict):
            actual_status = response.get("status_code")
            body = response.get("body")
        else:
            actual_status = response.status_code
            try:
                body = response.json()
            except Exception:
                body = None
    except Exception as e:
        return ErrorValidationResult(
            valid=False,
            expected_status=expected_status,
            actual_status=None,
            aip193_error=None,
            message=f"Failed to extract response data: {e}",
        )

    # Validate status code is present
    if actual_status is None:
        return ErrorValidationResult(
            valid=False,
            expected_status=expected_status,
            actual_status=None,
            aip193_error=None,
            message="Response does not contain a status code",
        )

    # Validate status code is an integer
    if not isinstance(actual_status, int):
        return ErrorValidationResult(
            valid=False,
            expected_status=expected_status,
            actual_status=None,
            aip193_error=None,
            message=f"Status code is not an integer: {type(actual_status).__name__}",
        )

    # Parse AIP-193 error if body is a dict with 'error' key
    aip193_error = None
    if isinstance(body, dict) and "error" in body:
        try:
            aip193_error = AIP193Error.from_dict(body)
        except ValueError as e:
            return ErrorValidationResult(
                valid=False,
                expected_status=expected_status,
                actual_status=actual_status,
                aip193_error=None,
                message=f"Invalid AIP-193 error: {e}",
            )

    # Compare status codes
    if actual_status == expected_status:
        return ErrorValidationResult(
            valid=True,
            expected_status=expected_status,
            actual_status=actual_status,
            aip193_error=aip193_error,
            message=f"Status code matches: {expected_error} ({expected_status})",
        )

    # Status code mismatch
    possible_errors = STATUS_TO_ERRORS.get(actual_status, [])
    actual_error_info = f" (could be: {', '.join(possible_errors)})" if possible_errors else ""

    return ErrorValidationResult(
        valid=False,
        expected_status=expected_status,
        actual_status=actual_status,
        aip193_error=aip193_error,
        message=f"Status code mismatch: expected {expected_error} ({expected_status}), "
        f"got {actual_status}{actual_error_info}",
    )


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
