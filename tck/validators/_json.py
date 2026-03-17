"""Shared JSON payload extractors and validators.

Both JSON-RPC and HTTP+JSON transports use JSON dicts for responses.
The only difference is envelope unwrapping: JSON-RPC wraps the payload
in ``{"result": ...}``, while HTTP+JSON uses the dict directly.

This module operates on the already-unwrapped ``dict``, so both
transports can delegate here after stripping their envelope.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from tck.requirements.base import TaskStateBinding


# ---------------------------------------------------------------------------
# Response-level extractors (operate on the unwrapped dict)
# ---------------------------------------------------------------------------


def extract_artifacts(result: dict[str, Any]) -> list[Any]:
    """Extract artifacts from an unwrapped SendMessageResponse dict."""
    task = result.get("task", {})
    if isinstance(task, dict):
        return task.get("artifacts", [])
    return []


def extract_message(result: dict[str, Any]) -> Any | None:
    """Extract a Message payload from an unwrapped SendMessageResponse dict."""
    return result.get("message")


# ---------------------------------------------------------------------------
# Part-level extractors
# ---------------------------------------------------------------------------


def get_part_type(part: Any) -> str | None:
    """Determine which oneof content variant is set on a Part."""
    if isinstance(part, dict):
        for key in ("text", "raw", "url", "data"):
            if part.get(key):
                return key
    return None


def get_part_text(part: Any) -> str | None:
    """Extract text content from a Part."""
    if isinstance(part, dict):
        return part.get("text")
    return None


def get_part_filename(part: Any) -> str | None:
    """Extract filename from a Part."""
    if isinstance(part, dict):
        return part.get("filename") or None
    return None


def get_part_media_type(part: Any) -> str | None:
    """Extract media type from a Part."""
    if isinstance(part, dict):
        return part.get("mediaType") or None
    return None


def get_part_data(part: Any) -> Any | None:
    """Extract data content from a Part."""
    if isinstance(part, dict):
        return part.get("data")
    return None


# ---------------------------------------------------------------------------
# Artifact-level extractors
# ---------------------------------------------------------------------------


def get_artifact_id(artifact: Any) -> str | None:
    """Extract artifactId from an Artifact."""
    if isinstance(artifact, dict):
        return artifact.get("artifactId") or None
    return None


def get_artifact_parts(artifact: Any) -> list[Any]:
    """Extract parts from an Artifact."""
    if isinstance(artifact, dict):
        return artifact.get("parts", [])
    return []


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_task_state(
    result: dict[str, Any],
    expected: TaskStateBinding,
    error_prefix: str = "Response",
) -> list[str]:
    """Validate that the task in an unwrapped response dict has the expected state."""
    task = result.get("task")
    if not isinstance(task, dict):
        return [f"{error_prefix} does not contain a task, cannot check state '{expected.json_value}'"]
    actual = task.get("status", {}).get("state", "")
    if actual != expected.json_value:
        return [f"Expected task state '{expected.json_value}' but got '{actual}'"]
    return []


def validate_message_response_contains_field(
    result: dict[str, Any],
    field: str,
    error_prefix: str = "Response",
) -> list[str]:
    """Validate that a field is present in an unwrapped response dict."""
    inner = result.get("task") or result.get("message") or result
    if inner.get(field) is None:
        return [f"{error_prefix} must include '{field}'"]
    return []
