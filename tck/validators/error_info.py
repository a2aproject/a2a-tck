"""Shared ErrorInfo validation for ProtoJSON error responses.

Provides helpers to find and validate ``google.rpc.ErrorInfo`` entries
in the ``data`` (JSON-RPC) or ``details`` (HTTP+JSON) arrays that use
the ProtoJSON ``@type`` convention.  The gRPC transport uses binary
protobuf parsing instead (see ``grpc/error_validator.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from google.rpc import error_details_pb2

from tck.requirements.base import A2A_ERROR_DOMAIN, A2A_ERROR_REASONS


ERRORINFO_TYPE = "type.googleapis.com/google.rpc.ErrorInfo"
WELL_KNOWN_ERROR_DETAIL_TYPES = frozenset(
    f"type.googleapis.com/{descriptor.full_name}"
    for descriptor in error_details_pb2.DESCRIPTOR.message_types_by_name.values()
)


def validate_error_details(details: Any) -> list[str]:
    """Validate a present error-details field without requiring a particular Any type."""
    if not isinstance(details, list):
        return ["Error details must be an array"]
    errors = []
    for index, item in enumerate(details):
        if not isinstance(item, dict):
            errors.append(f"Error detail {index} must be an object")
        elif not isinstance(item.get("@type"), str) or not item["@type"]:
            errors.append(f"Error detail {index} must include a non-empty @type string")
    return errors


def uses_well_known_error_details(details: Any) -> bool:
    """Check the recommendation without treating a custom Any type as malformed."""
    return not validate_error_details(details) and any(
        item["@type"] in WELL_KNOWN_ERROR_DETAIL_TYPES for item in details
    )


def find_error_info(details: list[Any]) -> dict[str, Any] | None:
    """Find the ``google.rpc.ErrorInfo`` entry in a ProtoJSON array.

    Works for both JSON-RPC ``error.data`` and HTTP+JSON ``error.details``.

    Returns:
        The ErrorInfo dict if found, or ``None``.
    """
    for item in details:
        if isinstance(item, dict) and item.get("@type") == ERRORINFO_TYPE:
            return item
    return None


@dataclass
class ErrorInfoResult:
    """Result of ErrorInfo validation."""

    valid: bool
    message: str


def validate_error_info(
    details: list[Any],
    *,
    expected_reason: str | None = None,
) -> ErrorInfoResult:
    """Validate the ``google.rpc.ErrorInfo`` entry in a ProtoJSON array.

    Checks:
    1. An ErrorInfo entry exists in the array.
    2. Its ``domain`` equals ``"a2a-protocol.org"``.
    3. Its ``reason`` is a recognised A2A error reason.
    4. If *expected_reason* is given, the reason matches exactly.

    Args:
        details: The ProtoJSON array (``error.data`` or ``error.details``).
        expected_reason: If set, require this exact reason value.

    Returns:
        An :class:`ErrorInfoResult` with validation status and message.
    """
    errors = validate_error_details(details)
    if errors:
        return ErrorInfoResult(valid=False, message="; ".join(errors))
    error_info = find_error_info(details)
    if error_info is None:
        return ErrorInfoResult(
            valid=False,
            message=(
                f"Array must contain a google.rpc.ErrorInfo entry "
                f"with @type '{ERRORINFO_TYPE}'"
            ),
        )

    domain = error_info.get("domain", "")
    if domain != A2A_ERROR_DOMAIN:
        return ErrorInfoResult(
            valid=False,
            message=f"ErrorInfo domain must be {A2A_ERROR_DOMAIN!r}, got {domain!r}",
        )

    reason = error_info.get("reason", "")
    if not isinstance(reason, str) or reason not in A2A_ERROR_REASONS:
        return ErrorInfoResult(
            valid=False,
            message=f"ErrorInfo reason {reason!r} is not a recognised A2A error reason",
        )

    if expected_reason is not None and reason != expected_reason:
        return ErrorInfoResult(
            valid=False,
            message=(
                f"ErrorInfo reason should be {expected_reason!r}, got {reason!r}"
            ),
        )

    return ErrorInfoResult(valid=True, message="ErrorInfo is valid")
