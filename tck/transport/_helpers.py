"""Shared helpers for A2A transport clients."""

from __future__ import annotations

import json

from typing import TYPE_CHECKING, Any, Iterator


if TYPE_CHECKING:
    import httpx

A2A_VERSION_HEADER = "A2A-Version"
A2A_EXTENSIONS_HEADER = "A2A-Extensions"
A2A_VERSION = "1.0"


def get_required_extensions(agent_card: dict) -> list[str]:
    """Extract required extension URIs from an Agent Card.

    Per A2A spec §8.3.3, ``capabilities.extensions[]`` entries with
    ``required: true`` must be activated on every request via the
    ``A2A-Extensions`` header (HTTP) or ``a2a-extensions`` metadata (gRPC).

    Returns a list of extension URIs (may be empty).
    """
    caps = agent_card.get("capabilities", {})
    extensions = caps.get("extensions", [])
    return [
        ext["uri"]
        for ext in extensions
        if isinstance(ext, dict) and ext.get("required") and ext.get("uri")
    ]


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
