"""HTTP+JSON payload validators and extractors for A2A protocol responses.

Delegates to :mod:`tck.validators._json` after basic type checking
of the raw response dict (no envelope unwrapping needed).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tck.validators import _json


if TYPE_CHECKING:
    from tck.requirements.base import TaskStateBinding


# ---------------------------------------------------------------------------
# Envelope unwrapping (identity — HTTP+JSON has no envelope)
# ---------------------------------------------------------------------------


def _unwrap(response: Any) -> dict[str, Any]:
    """Return the raw response as a dict, or empty dict if not a dict."""
    data = response.raw_response
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def extract_artifacts(response: Any) -> list[Any]:
    """Extract artifacts from an HTTP+JSON SendMessageResponse."""
    return _json.extract_artifacts(_unwrap(response))

def extract_message(response: Any) -> Any | None:
    """Extract a Message payload from an HTTP+JSON SendMessageResponse."""
    return _json.extract_message(_unwrap(response))

get_part_type = _json.get_part_type
get_part_text = _json.get_part_text
get_part_filename = _json.get_part_filename
get_part_media_type = _json.get_part_media_type
get_part_data = _json.get_part_data
get_artifact_id = _json.get_artifact_id
get_artifact_parts = _json.get_artifact_parts


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_task_state(response: Any, expected: TaskStateBinding) -> list[str]:
    """Validate that the task has the expected state."""
    data = response.raw_response
    if not isinstance(data, dict):
        return [f"Response is not a JSON object, cannot check state '{expected.json_value}'"]
    return _json.validate_task_state(data, expected)


def validate_message_response_contains_field(
    response: Any, field: str,
) -> list[str]:
    """Validate that a field is present in the SendMessageResponse body."""
    data = response.raw_response
    if not isinstance(data, dict):
        return [f"Response is not a JSON object, cannot check for '{field}'"]
    return _json.validate_message_response_contains_field(data, field)
