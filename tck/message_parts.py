"""Load operator-supplied Message.parts for generic requirement scenarios."""

from __future__ import annotations

import json

from pathlib import Path
from typing import Any


class MessagePartsError(ValueError):
    """Raised when a message-parts fixture cannot be loaded safely."""


def load_message_parts(path: str | Path) -> list[dict[str, Any]]:
    """Load and validate a non-empty JSON array of A2A Part objects."""
    fixture_path = Path(path)
    try:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MessagePartsError(
            f"Unable to load message parts from {fixture_path}: {exc}"
        ) from exc

    if not isinstance(payload, list) or not payload:
        raise MessagePartsError("Message parts fixture must be a non-empty JSON array")
    if not all(isinstance(part, dict) for part in payload):
        raise MessagePartsError("Every message part must be a JSON object")
    return payload
