"""Shared helpers for A2A transport clients."""

from __future__ import annotations

import json

from typing import TYPE_CHECKING, Any, Iterator


if TYPE_CHECKING:
    import httpx

A2A_VERSION_HEADER = "A2A-Version"
A2A_VERSION = "1.0"


def _build_params(**kwargs: Any) -> dict:
    """Build a params dict, omitting None values."""
    return {k: v for k, v in kwargs.items() if v is not None}


def _stream_sse(response: httpx.Response) -> Iterator[dict]:
    """Yield parsed SSE events from a streaming httpx response.

    Reads the response body incrementally so that events are available
    as soon as they arrive rather than waiting for the stream to close.
    """
    for raw_line in response.iter_lines():
        line = raw_line.strip()
        if line.startswith("data:"):
            data = line[len("data:"):].strip()
            if data:
                yield json.loads(data)
