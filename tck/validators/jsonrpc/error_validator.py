"""JSON-RPC error validator for A2A protocol responses.

This module provides validation of JSON-RPC error responses according to
the error code mappings defined in Section 9 of the A2A specification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# JSON-RPC error codes as defined in A2A specification Section 9
# Standard JSON-RPC errors (-32600 to -32699)
# A2A-specific errors (-32001 to -32099)
JSONRPC_ERROR_CODES: dict[str, int] = {
    # A2A-specific errors
    "TaskNotFoundError": -32001,
    "TaskNotCancelableError": -32002,
    "PushNotificationNotSupportedError": -32003,
    "UnsupportedOperationError": -32004,
    "ContentTypeNotSupportedError": -32005,
    "InvalidAgentResponseError": -32006,
    "VersionNotSupportedError": -32009,
    # Standard JSON-RPC errors
    "InvalidRequestError": -32600,
    "MethodNotFoundError": -32601,
    "InvalidParamsError": -32602,
    "InternalError": -32603,
    "ParseError": -32700,
}

# Reverse mapping from error codes to error names
ERROR_CODE_NAMES: dict[int, str] = {v: k for k, v in JSONRPC_ERROR_CODES.items()}


@dataclass
class ErrorValidationResult:
    """Result of a JSON-RPC error validation.

    Attributes:
        valid: True if the error response matches the expected error.
        expected_code: The expected error code.
        actual_code: The actual error code from the response (or None if missing).
        message: A descriptive message about the validation result.
    """

    valid: bool
    expected_code: int
    actual_code: int | None
    message: str


def validate_jsonrpc_error(
    response: dict[str, Any], expected_error: str
) -> ErrorValidationResult:
    """Validate a JSON-RPC error response against an expected error type.

    Args:
        response: The JSON-RPC response dict containing an 'error' field.
        expected_error: The expected error name (e.g., "TaskNotFoundError").

    Returns:
        An ErrorValidationResult with validation status and details.

    Example:
        >>> response = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32001, "message": "Task not found"}}
        >>> result = validate_jsonrpc_error(response, "TaskNotFoundError")
        >>> print(result.valid)
        True
    """
    # Get the expected error code
    if expected_error not in JSONRPC_ERROR_CODES:
        return ErrorValidationResult(
            valid=False,
            expected_code=0,
            actual_code=None,
            message=f"Unknown error type: {expected_error}. "
            f"Valid types: {', '.join(sorted(JSONRPC_ERROR_CODES.keys()))}",
        )

    expected_code = JSONRPC_ERROR_CODES[expected_error]

    # Check if response has an 'error' field
    if "error" not in response:
        return ErrorValidationResult(
            valid=False,
            expected_code=expected_code,
            actual_code=None,
            message="Response does not contain an 'error' field",
        )

    error = response["error"]

    # Check if error is a dict with required fields
    if not isinstance(error, dict):
        return ErrorValidationResult(
            valid=False,
            expected_code=expected_code,
            actual_code=None,
            message=f"Error field is not an object: {type(error).__name__}",
        )

    # Check for 'code' field
    if "code" not in error:
        return ErrorValidationResult(
            valid=False,
            expected_code=expected_code,
            actual_code=None,
            message="Error object does not contain a 'code' field",
        )

    actual_code = error["code"]

    # Validate code is an integer
    if not isinstance(actual_code, int):
        return ErrorValidationResult(
            valid=False,
            expected_code=expected_code,
            actual_code=None,
            message=f"Error code is not an integer: {type(actual_code).__name__}",
        )

    # Compare error codes
    if actual_code == expected_code:
        return ErrorValidationResult(
            valid=True,
            expected_code=expected_code,
            actual_code=actual_code,
            message=f"Error code matches: {expected_error} ({expected_code})",
        )

    # Error code mismatch
    actual_name = ERROR_CODE_NAMES.get(actual_code, "Unknown")
    return ErrorValidationResult(
        valid=False,
        expected_code=expected_code,
        actual_code=actual_code,
        message=f"Error code mismatch: expected {expected_error} ({expected_code}), "
        f"got {actual_name} ({actual_code})",
    )


def get_error_name(code: int) -> str | None:
    """Get the error name for a given error code.

    Args:
        code: The JSON-RPC error code.

    Returns:
        The error name, or None if the code is unknown.
    """
    return ERROR_CODE_NAMES.get(code)


def get_error_code(name: str) -> int | None:
    """Get the error code for a given error name.

    Args:
        name: The error name (e.g., "TaskNotFoundError").

    Returns:
        The error code, or None if the name is unknown.
    """
    return JSONRPC_ERROR_CODES.get(name)
