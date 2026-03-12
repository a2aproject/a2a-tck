"""Validators for streaming transport responses."""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from tck.transport.base import StreamingResponse


def drain_stream(response: StreamingResponse) -> None:
    """Consume remaining events from a streaming response.

    Ensures the underlying transport stream (e.g. gRPC HTTP/2) is properly
    closed and does not poison the shared channel for subsequent tests.
    """
    try:
        for _ in response.events:
            pass
    except Exception:
        pass


def validate_streaming_events(response: StreamingResponse) -> list[str]:
    """Validate that a streaming response produces at least one event, then drain."""
    errors: list[str] = []
    try:
        first_event = next(response.events)
        if first_event is None:
            errors.append("Streaming response yielded None as first event")
    except StopIteration:
        errors.append("Streaming response produced no events")
    except Exception as exc:
        errors.append(f"Streaming iteration failed: {exc}")
    finally:
        drain_stream(response)
    return errors
