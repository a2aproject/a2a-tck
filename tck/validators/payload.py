"""Transport-agnostic payload validators for A2A protocol responses.

This module provides validator factories that return callables compatible
with ``RequirementSpec.validator(response, transport) -> list[str]``.
Transport-specific details (field name conventions, response structure)
are handled internally.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tck.validators.grpc.payload import (
    validate_message_response_contains_field as _grpc_validate,
)
from tck.validators.http_json.payload import (
    validate_message_response_contains_field as _http_json_validate,
)
from tck.validators.jsonrpc.payload import (
    validate_message_response_contains_field as _jsonrpc_validate,
)

_TRANSPORT_VALIDATORS = {
    "grpc": _grpc_validate,
    "jsonrpc": _jsonrpc_validate,
    "http_json": _http_json_validate,
}


def _to_snake_case(name: str) -> str:
    """Convert a camelCase field name to snake_case for gRPC protobuf access."""
    result: list[str] = []
    for ch in name:
        if ch.isupper():
            result.append("_")
            result.append(ch.lower())
        else:
            result.append(ch)
    return "".join(result).lstrip("_")


def validate_message_response_contains_field(
    field: str,
) -> Callable[[Any, str], list[str]]:
    """Return a validator that checks a field is present in a SendMessageResponse.

    Unwraps the SendMessageResponse envelope (``task`` or ``message``) before
    checking the field.

    Args:
        field: The camelCase field name (e.g. "contextId"). Automatically
               converted to snake_case for gRPC transports.

    Returns:
        A callable ``(response, transport) -> list[str]`` suitable for
        ``RequirementSpec.validator``.
    """
    grpc_field = _to_snake_case(field)

    def _validate(response: Any, transport: str) -> list[str]:
        validate = _TRANSPORT_VALIDATORS.get(transport)
        if validate is None:
            return []
        f = grpc_field if transport == "grpc" else field
        return validate(response, f)

    return _validate
