"""Shared helpers for A2A transport clients."""

from __future__ import annotations

import json

from typing import Any, Iterator


def _build_params(**kwargs: Any) -> dict:
    """Build a params dict, omitting None values."""
    return {k: v for k, v in kwargs.items() if v is not None}


def _parse_sse(text: str) -> Iterator[dict]:
    """Parse SSE-formatted text into JSON dicts."""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("data:"):
            data = line[len("data:"):].strip()
            if data:
                yield json.loads(data)
