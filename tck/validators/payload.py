"""Transport-agnostic payload validators and extractors for A2A protocol responses.

This module provides validator factories that return callables compatible
with ``RequirementSpec.validator(response, transport) -> list[str]``.

It also provides transport-aware extraction helpers for artifacts, messages,
and parts from ``TransportResponse`` objects.  Each function accepts
a ``transport`` string and dispatches to the appropriate transport-specific
implementation in ``tck.validators.{grpc,jsonrpc,http_json}.payload``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tck.validators.grpc import payload as _grpc
from tck.validators.http_json import payload as _http_json
from tck.validators.jsonrpc import payload as _jsonrpc


if TYPE_CHECKING:
    from collections.abc import Callable

    from tck.requirements.base import TaskStateBinding

_TRANSPORT_VALIDATORS = {
    "grpc": _grpc.validate_message_response_contains_field,
    "jsonrpc": _jsonrpc.validate_message_response_contains_field,
    "http_json": _http_json.validate_message_response_contains_field,
}

_STATE_VALIDATORS = {
    "grpc": _grpc.validate_task_state,
    "jsonrpc": _jsonrpc.validate_task_state,
    "http_json": _http_json.validate_task_state,
}

_TRANSPORT_MODULES = {
    "grpc": _grpc,
    "jsonrpc": _jsonrpc,
    "http_json": _http_json,
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


# ---------------------------------------------------------------------------
# Validator factories
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Transport-aware extraction helpers
# ---------------------------------------------------------------------------


def extract_artifacts(response: Any, transport: str) -> list[Any]:
    """Extract artifacts from a SendMessageResponse."""
    mod = _TRANSPORT_MODULES.get(transport)
    return mod.extract_artifacts(response) if mod else []


def extract_message(response: Any, transport: str) -> Any | None:
    """Extract a Message payload from a SendMessageResponse."""
    mod = _TRANSPORT_MODULES.get(transport)
    return mod.extract_message(response) if mod else None


def extract_history(response: Any, transport: str) -> list[Any]:
    """Extract history messages from a response."""
    mod = _TRANSPORT_MODULES.get(transport)
    return mod.extract_history(response) if mod else []


def get_part_type(part: Any, transport: str) -> str | None:
    """Determine which oneof content variant is set on a Part."""
    mod = _TRANSPORT_MODULES.get(transport)
    return mod.get_part_type(part) if mod else None


def get_part_text(part: Any, transport: str) -> str | None:
    """Extract text content from a Part."""
    mod = _TRANSPORT_MODULES.get(transport)
    return mod.get_part_text(part) if mod else None


def get_part_filename(part: Any, transport: str) -> str | None:
    """Extract filename from a Part."""
    mod = _TRANSPORT_MODULES.get(transport)
    return mod.get_part_filename(part) if mod else None


def get_part_media_type(part: Any, transport: str) -> str | None:
    """Extract media type from a Part."""
    mod = _TRANSPORT_MODULES.get(transport)
    return mod.get_part_media_type(part) if mod else None


def get_part_data(part: Any, transport: str) -> Any | None:
    """Extract data content from a Part."""
    mod = _TRANSPORT_MODULES.get(transport)
    return mod.get_part_data(part) if mod else None


def get_artifact_id(artifact: Any, transport: str) -> str | None:
    """Extract artifactId from an Artifact."""
    mod = _TRANSPORT_MODULES.get(transport)
    return mod.get_artifact_id(artifact) if mod else None


def get_artifact_parts(artifact: Any, transport: str) -> list[Any]:
    """Extract parts from an Artifact."""
    mod = _TRANSPORT_MODULES.get(transport)
    return mod.get_artifact_parts(artifact) if mod else []


def validate_artifact_structure(
    response: Any,
    transport: str,
    expected_part_type: str,
) -> tuple[list[str], Any | None]:
    """Validate that the response contains an artifact with the expected part type.

    Returns (errors, first_part) so callers can do content-level checks.
    """
    errors: list[str] = []
    artifacts = extract_artifacts(response, transport)
    if not artifacts:
        errors.append("Response contains no artifacts")
        return errors, None

    artifact = artifacts[0]
    aid = get_artifact_id(artifact, transport)
    if not aid:
        errors.append("Artifact is missing artifactId")

    parts = get_artifact_parts(artifact, transport)
    if not parts:
        errors.append("Artifact has no parts")
        return errors, None

    part = parts[0]
    part_type = get_part_type(part, transport)
    if part_type != expected_part_type:
        errors.append(
            f"Expected part type '{expected_part_type}', got '{part_type}'"
        )

    return errors, part
