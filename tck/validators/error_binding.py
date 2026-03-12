"""Cross-transport expected-error validator.

Validates that a transport response (including streaming responses where
errors may arrive during iteration) matches the expected ErrorBinding
from a requirement specification.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from tck.requirements.base import ErrorBinding
    from tck.transport.base import StreamingResponse


def validate_expected_error(
    response: Any,
    transport: str,
    expected: ErrorBinding,
) -> list[str]:
    """Validate that a response matches the expected error binding.

    For non-streaming responses, checks ``response.success`` and
    ``response.error_code``.  For streaming responses where
    ``success=True``, delegates to :func:`_validate_from_stream`
    because the error may arrive during iteration (e.g. gRPC status)
    or as an error event (e.g. JSON-RPC envelope).

    Returns:
        A list of error strings (empty means validation passed).
    """
    from tck.transport.base import StreamingResponse

    if response.success:
        if isinstance(response, StreamingResponse):
            return _validate_from_stream(response, transport, expected)
        return [f"Expected {expected.name} but operation succeeded"]

    expected_code = expected.expected_code(transport)
    actual_code = response.error_code
    if expected_code is not None and actual_code != expected_code:
        return [
            f"Expected error code {expected_code} "
            f"({expected.name}), got {actual_code}"
        ]

    return []


def _validate_from_stream(
    response: StreamingResponse,
    transport: str,
    expected: ErrorBinding,
) -> list[str]:
    """Check if the expected error arrives during streaming iteration.

    Handles three delivery patterns:

    1. **gRPC**: Error raised as an exception (e.g. ``grpc.RpcError``)
       when iterating events.  The exception's ``.code().name`` is
       compared to the expected gRPC status.
    2. **JSON-RPC**: Error delivered as an SSE event containing an
       ``"error"`` key with a JSON-RPC error code.
    3. **HTTP+JSON**: Error delivered as an SSE event containing an
       ``"error"`` key (same check as JSON-RPC).
    """
    try:
        first_event = next(response.events)
    except StopIteration:
        return [f"Expected {expected.name} but stream was empty (no error)"]
    except Exception as exc:
        # gRPC: error arrives as an exception during iteration
        actual_code = None
        if hasattr(exc, "code"):
            actual_code = exc.code().name
        expected_code = expected.expected_code(transport)
        if expected_code is not None and actual_code != expected_code:
            return [
                f"Expected error code {expected_code} "
                f"({expected.name}), got {actual_code}"
            ]
        return []

    # JSON-RPC / HTTP+JSON: error may arrive as an event with an "error" key
    if isinstance(first_event, dict) and "error" in first_event:
        actual_code = first_event["error"].get("code")
        expected_code = expected.expected_code(transport)
        if expected_code is not None and actual_code != expected_code:
            return [
                f"Expected error code {expected_code} "
                f"({expected.name}), got {actual_code}"
            ]
        return []

    return [f"Expected {expected.name} but streaming produced events"]
