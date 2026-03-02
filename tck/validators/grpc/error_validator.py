"""gRPC error validator for A2A protocol responses.

This module provides validation of gRPC error responses according to
the error code mappings defined in Section 5.4 of the A2A specification.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from google.rpc import error_details_pb2, status_pb2

from tck.requirements.base import ERROR_BINDINGS


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
    trailing_metadata = rpc_error.trailing_metadata()
    if trailing_metadata is None:
        return None

    # Look for the binary status details key.
    status_bin = None
    for key, value in trailing_metadata:
        if key == "grpc-status-details-bin":
            status_bin = value
            break

    if status_bin is None:
        return None

    # Parse as google.rpc.Status
    status_proto = status_pb2.Status()
    status_proto.ParseFromString(status_bin)

    # Search for ErrorInfo in the details
    for detail in status_proto.details:
        if detail.Is(error_details_pb2.ErrorInfo.DESCRIPTOR):
            error_info = error_details_pb2.ErrorInfo()
            detail.Unpack(error_info)
            return {
                "reason": error_info.reason,
                "domain": error_info.domain,
                "metadata": dict(error_info.metadata),
            }

    return None
