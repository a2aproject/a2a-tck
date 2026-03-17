"""Transport-agnostic payload validators for A2A protocol responses.

This module provides validator factories that return callables compatible
with ``RequirementSpec.validator(response, transport) -> list[str]``.
Transport-specific details (field name conventions, response structure)
are handled internally.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tck.validators.grpc.payload import (
    validate_message_response_contains_field as _grpc_validate,
)
from tck.validators.grpc.payload import (
    validate_task_state as _grpc_validate_state,
)
from tck.validators.http_json.payload import (
    validate_message_response_contains_field as _http_json_validate,
)
from tck.validators.http_json.payload import (
    validate_task_state as _http_json_validate_state,
)
from tck.validators.jsonrpc.payload import (
    validate_message_response_contains_field as _jsonrpc_validate,
)
from tck.validators.jsonrpc.payload import (
    validate_task_state as _jsonrpc_validate_state,
)


if TYPE_CHECKING:
    from collections.abc import Callable

    from tck.requirements.base import TaskStateBinding

_TRANSPORT_VALIDATORS = {
    "grpc": _grpc_validate,
    "jsonrpc": _jsonrpc_validate,
    "http_json": _http_json_validate,
}

_STATE_VALIDATORS = {
    "grpc": _grpc_validate_state,
    "jsonrpc": _jsonrpc_validate_state,
    "http_json": _http_json_validate_state,
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


def validate_task_state(
    response: Any,
    transport: str,
    expected: TaskStateBinding,
) -> list[str]:
    """Validate that the task in a SendMessageResponse has the expected state.

    Args:
        response: The transport response object.
        transport: Transport name (``"grpc"``, ``"jsonrpc"``, ``"http_json"``).
        expected: The expected ``TaskStateBinding``.

    Returns:
        A list of error strings (empty if the state matches).
    """
    validate = _STATE_VALIDATORS.get(transport)
    if validate is None:
        return []
    return validate(response, expected)
