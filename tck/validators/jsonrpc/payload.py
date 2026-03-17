"""JSON-RPC payload validators and extractors for A2A protocol responses.

Delegates to :mod:`tck.validators._json` after unwrapping the
``{"result": ...}`` envelope.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tck.validators import _json


if TYPE_CHECKING:
    from tck.requirements.base import TaskStateBinding


# ---------------------------------------------------------------------------
# Envelope unwrapping
# ---------------------------------------------------------------------------


def _unwrap_result(response: Any) -> dict[str, Any]:
    """Unwrap the JSON-RPC envelope to get the result dict."""
    data = response.raw_response
    if not isinstance(data, dict):
        return {}
    result = data.get("result", data)
    return result if isinstance(result, dict) else {}


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def extract_artifacts(response: Any) -> list[Any]:
    """Extract artifacts from a JSON-RPC SendMessageResponse."""
    return _json.extract_artifacts(_unwrap_result(response))

def extract_message(response: Any) -> Any | None:
    """Extract a Message payload from a JSON-RPC SendMessageResponse."""
    return _json.extract_message(_unwrap_result(response))

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
    return _json.validate_task_state(
        _unwrap_result(response), expected, error_prefix="Response result",
    )


def validate_message_response_contains_field(
    response: Any, field: str,
) -> list[str]:
    """Validate that a field is present in the SendMessageResponse result."""
    return _json.validate_message_response_contains_field(
        _unwrap_result(response), field, error_prefix="Response result",
    )
