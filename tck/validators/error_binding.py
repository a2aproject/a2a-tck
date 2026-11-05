"""Cross-transport expected-error validator.

Validates that a transport response matches the expected ErrorBinding
from a requirement specification.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tck.validators.grpc.error_validator import validate_grpc_error
from tck.validators.http_json.error_validator import validate_http_json_error


if TYPE_CHECKING:
    from tck.requirements.base import ErrorBinding
    from tck.transport.base import TransportResponse


def validate_expected_error(
    response: TransportResponse,
    transport: str,
    expected: ErrorBinding,
) -> list[str]:
    """Validate that a response matches the expected error binding.

    Returns:
        A list of error strings (empty means validation passed).
    """
    if response.success:
        return [f"Expected {expected.name} but operation succeeded"]

    if transport == "http_json":
        result = validate_http_json_error(
            {"status_code": response.status_code, "body": response.raw_response}, expected.name,
        )
        return [] if result.valid else [result.message]
    if transport == "grpc":
        result = validate_grpc_error(response.raw_response, expected.name)
        return [] if result.valid else [result.message]
    if transport != "jsonrpc":
        return [f"Unknown transport: {transport}"]
    expected_code = expected.expected_code(transport)
    actual_code = response.error_code
    if expected_code is not None and actual_code != expected_code:
        return [
            f"Expected error code {expected_code} "
            f"({expected.name}), got {actual_code}"
        ]

    return []
