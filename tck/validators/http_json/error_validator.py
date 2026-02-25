"""HTTP+JSON error validator for A2A protocol responses.

This module provides validation of HTTP+JSON error responses according to
Section 11 of the A2A specification, including RFC 7807 Problem Details support.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


# HTTP status code mappings for A2A errors
# Based on A2A specification Section 11
HTTP_JSON_ERROR_STATUS: dict[str, int] = {
    "TaskNotFoundError": 404,
    "TaskNotCancelableError": 400,
    "PushNotificationNotSupportedError": 400,
    "UnsupportedOperationError": 400,
    "ContentTypeNotSupportedError": 415,
    "InvalidAgentResponseError": 500,
    "VersionNotSupportedError": 400,
    "InvalidRequestError": 400,
    "MethodNotFoundError": 404,
    "InvalidParamsError": 400,
    "InternalError": 500,
}

# Reverse mapping from status codes to possible error names
# Note: Multiple errors can map to the same status code
STATUS_TO_ERRORS: dict[int, list[str]] = {}
for _name, _status in HTTP_JSON_ERROR_STATUS.items():
    STATUS_TO_ERRORS.setdefault(_status, []).append(_name)


@dataclass
class ProblemDetails:
    """RFC 7807 Problem Details structure.

    This dataclass represents the standard problem details format for HTTP APIs
    as defined in RFC 7807 (https://tools.ietf.org/html/rfc7807).

    Attributes:
        type: A URI reference that identifies the problem type.
        title: A short, human-readable summary of the problem type.
        status: The HTTP status code for this occurrence of the problem.
        detail: A human-readable explanation specific to this occurrence.
        instance: A URI reference that identifies the specific occurrence.
    """

    type: str
    title: str
    status: int
    detail: str = ""
    instance: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProblemDetails:
        """Create a ProblemDetails instance from a dictionary.

        Args:
            data: A dictionary containing problem details fields.

        Returns:
            A ProblemDetails instance.

        Raises:
            ValueError: If required fields are missing.
        """
        if "type" not in data:
            raise ValueError("Problem details missing required 'type' field")
        if "title" not in data:
            raise ValueError("Problem details missing required 'title' field")
        if "status" not in data:
            raise ValueError("Problem details missing required 'status' field")

        return cls(
            type=str(data["type"]),
            title=str(data["title"]),
            status=int(data["status"]),
            detail=str(data.get("detail", "")),
            instance=str(data.get("instance", "")),
        )


@dataclass
class ErrorValidationResult:
    """Result of an HTTP+JSON error validation.

    Attributes:
        valid: True if the error response matches the expected error.
        expected_status: The expected HTTP status code.
        actual_status: The actual HTTP status code from the response.
        problem_details: Parsed RFC 7807 Problem Details, if present.
        message: A descriptive message about the validation result.
    """

    valid: bool
    expected_status: int
    actual_status: int | None
    problem_details: ProblemDetails | None = None
    message: str = ""


class HTTPResponse(Protocol):
    """Protocol for HTTP response objects.

    This protocol defines the minimal interface required for HTTP responses
    to be validated. It is compatible with httpx.Response and similar libraries.
    """

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

    Example:
        >>> response = {"status_code": 404, "headers": {}, "body": {"type": "...", "title": "Not Found", "status": 404}}
        >>> result = validate_http_json_error(response, "TaskNotFoundError")
        >>> print(result.valid)
        True
    """
    # Get the expected status code
    if expected_error not in HTTP_JSON_ERROR_STATUS:
        return ErrorValidationResult(
            valid=False,
            expected_status=0,
            actual_status=None,
            problem_details=None,
            message=f"Unknown error type: {expected_error}. "
            f"Valid types: {', '.join(sorted(HTTP_JSON_ERROR_STATUS.keys()))}",
        )

    expected_status = HTTP_JSON_ERROR_STATUS[expected_error]

    # Extract status code and body from response
    try:
        if isinstance(response, dict):
            actual_status = response.get("status_code")
            headers = response.get("headers", {})
            body = response.get("body")
        else:
            actual_status = response.status_code
            headers = dict(response.headers)
            try:
                body = response.json()
            except Exception:
                body = None
    except Exception as e:
        return ErrorValidationResult(
            valid=False,
            expected_status=expected_status,
            actual_status=None,
            problem_details=None,
            message=f"Failed to extract response data: {e}",
        )

    # Validate status code is present
    if actual_status is None:
        return ErrorValidationResult(
            valid=False,
            expected_status=expected_status,
            actual_status=None,
            problem_details=None,
            message="Response does not contain a status code",
        )

    # Validate status code is an integer
    if not isinstance(actual_status, int):
        return ErrorValidationResult(
            valid=False,
            expected_status=expected_status,
            actual_status=None,
            problem_details=None,
            message=f"Status code is not an integer: {type(actual_status).__name__}",
        )

    # Parse Problem Details if Content-Type indicates it
    problem_details = None
    content_type = _get_content_type(headers)
    if content_type and "application/problem+json" in content_type.lower() and isinstance(body, dict):
        try:
            problem_details = ProblemDetails.from_dict(body)
        except ValueError as e:
            return ErrorValidationResult(
                valid=False,
                expected_status=expected_status,
                actual_status=actual_status,
                problem_details=None,
                message=f"Invalid Problem Details: {e}",
            )

    # Compare status codes
    if actual_status == expected_status:
        return ErrorValidationResult(
            valid=True,
            expected_status=expected_status,
            actual_status=actual_status,
            problem_details=problem_details,
            message=f"Status code matches: {expected_error} ({expected_status})",
        )

    # Status code mismatch
    possible_errors = STATUS_TO_ERRORS.get(actual_status, [])
    actual_error_info = f" (could be: {', '.join(possible_errors)})" if possible_errors else ""

    return ErrorValidationResult(
        valid=False,
        expected_status=expected_status,
        actual_status=actual_status,
        problem_details=problem_details,
        message=f"Status code mismatch: expected {expected_error} ({expected_status}), "
        f"got {actual_status}{actual_error_info}",
    )


def _get_content_type(headers: dict[str, str]) -> str | None:
    """Get the Content-Type header value (case-insensitive).

    Args:
        headers: The response headers dict.

    Returns:
        The Content-Type value, or None if not present.
    """
    for key, value in headers.items():
        if key.lower() == "content-type":
            return value
    return None


def get_expected_status(error_name: str) -> int | None:
    """Get the expected HTTP status code for an error name.

    Args:
        error_name: The error name (e.g., "TaskNotFoundError").

    Returns:
        The expected HTTP status code, or None if unknown.
    """
    return HTTP_JSON_ERROR_STATUS.get(error_name)


def get_possible_errors(status_code: int) -> list[str]:
    """Get the possible error names for a given HTTP status code.

    Args:
        status_code: The HTTP status code.

    Returns:
        A list of possible error names, or empty list if unknown.
    """
    return STATUS_TO_ERRORS.get(status_code, [])
