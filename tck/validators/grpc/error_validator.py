"""gRPC error validator for A2A protocol responses.

This module provides validation of gRPC error responses according to
the error code mappings defined in Section 5.4 of the A2A specification.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from google.protobuf.message import DecodeError
from google.rpc import error_details_pb2, status_pb2

from tck.requirements.base import ERROR_BINDINGS
from tck.validators.error_info import ERRORINFO_TYPE, validate_error_info


if TYPE_CHECKING:
    import grpc


# gRPC status mappings for A2A errors, derived from central ErrorBinding definitions.
# Only includes errors that have a gRPC status mapping.
GRPC_ERROR_STATUS: dict[str, str] = {
    name: binding.grpc_status
    for name, binding in ERROR_BINDINGS.items()
    if binding.grpc_status
}

# Reverse mapping from gRPC status to possible error names.
# Note: Multiple errors can map to the same status code.
STATUS_TO_ERRORS: dict[str, list[str]] = defaultdict(list)
for _name, _status in GRPC_ERROR_STATUS.items():
    STATUS_TO_ERRORS[_status].append(_name)
STATUS_TO_ERRORS = dict(STATUS_TO_ERRORS)


@dataclass
class ErrorValidationResult:
    """Result of a gRPC error validation.

    Attributes:
        valid: True if the error response matches the expected error.
        expected_status: The expected gRPC status code name.
        actual_status: The actual gRPC status code name from the response.
        message: A descriptive message about the validation result.
    """

    valid: bool
    expected_status: str
    actual_status: str | None
    message: str


def validate_grpc_error(
    rpc_error: grpc.RpcError, expected_error: str
) -> ErrorValidationResult:
    """Validate a gRPC error against an expected A2A error type.

    Args:
        rpc_error: The gRPC RpcError exception.
        expected_error: The expected error name (e.g., "TaskNotFoundError").

    Returns:
        An ErrorValidationResult with validation status and details.
    """
    if expected_error not in GRPC_ERROR_STATUS:
        return ErrorValidationResult(
            valid=False,
            expected_status="",
            actual_status=None,
            message=f"Unknown error type: {expected_error}. "
            f"Valid types: {', '.join(sorted(GRPC_ERROR_STATUS.keys()))}",
        )

    expected_status = GRPC_ERROR_STATUS[expected_error]
    actual_status = rpc_error.code().name

    if actual_status == expected_status:
        try:
            status = _parse_status_details(rpc_error)
            info = _error_info_from_status(status) if status is not None else None
        except DecodeError as error:
            return ErrorValidationResult(False, expected_status, actual_status, f"Malformed gRPC status details: {error}")
        if status is not None and status.code != rpc_error.code().value[0]:
            return ErrorValidationResult(False, expected_status, actual_status, "Binary status code must equal the gRPC status code")
        reason = ERROR_BINDINGS[expected_error].reason
        if reason is not None:
            identity = validate_error_info([{"@type": ERRORINFO_TYPE, **info}] if info is not None else [], expected_reason=reason)
            if not identity.valid:
                return ErrorValidationResult(False, expected_status, actual_status, identity.message)
        return ErrorValidationResult(
            valid=True,
            expected_status=expected_status,
            actual_status=actual_status,
            message=f"gRPC status matches: {expected_error} ({expected_status})",
        )

    possible_errors = STATUS_TO_ERRORS.get(actual_status, [])
    actual_info = f" (could be: {', '.join(possible_errors)})" if possible_errors else ""

    return ErrorValidationResult(
        valid=False,
        expected_status=expected_status,
        actual_status=actual_status,
        message=f"gRPC status mismatch: expected {expected_error} ({expected_status}), "
        f"got {actual_status}{actual_info}",
    )


def extract_error_info(rpc_error: grpc.RpcError) -> dict[str, Any] | None:
    """Extract google.rpc.ErrorInfo from a gRPC error's trailing metadata.

    Parses the google.rpc.Status from the ``grpc-status-details-bin`` trailing
    metadata key, then searches for a google.rpc.ErrorInfo detail message.

    Args:
        rpc_error: The gRPC RpcError exception.

    Returns:
        A dict with ``reason``, ``domain``, and ``metadata`` keys if ErrorInfo
        is found, or None otherwise.
    """
    try:
        status = _parse_status_details(rpc_error)
        return _error_info_from_status(status) if status is not None else None
    except DecodeError:
        return None


def _parse_status_details(rpc_error: grpc.RpcError) -> status_pb2.Status | None:
    """Decode the standard binary trailer once for identity and status checks."""
    for key, value in rpc_error.trailing_metadata() or ():
        if key == "grpc-status-details-bin":
            status = status_pb2.Status()
            status.ParseFromString(value)
            return status
    return None


def _error_info_from_status(status: status_pb2.Status) -> dict[str, Any] | None:
    """Extract the typed ErrorInfo without inventing a parallel domain validator."""
    for detail in status.details:
        if detail.Is(error_details_pb2.ErrorInfo.DESCRIPTOR):
            error_info = error_details_pb2.ErrorInfo()
            detail.Unpack(error_info)
            return {
                "reason": error_info.reason,
                "domain": error_info.domain,
                "metadata": dict(error_info.metadata),
            }
    return None
