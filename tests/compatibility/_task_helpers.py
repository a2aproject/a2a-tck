"""Shared helpers for creating tasks and extracting IDs across transports.

Many conformance tests need a real task to exist before they can exercise
an operation (GetTask, CancelTask, multi-turn, push notifications, …).
This module provides a transport-agnostic ``create_task`` function that
calls ``send_message`` and returns the resulting task/context IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient, TransportResponse


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAMPLE_MESSAGE: dict[str, Any] = {
    "role": "ROLE_USER",
    "parts": [{"text": "TCK prerequisite task creation"}],
    "messageId": "tck-task-helper-001",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass
class TaskInfo:
    """Identifiers extracted from a successful SendMessage response."""

    task_id: str
    context_id: str | None
    transport: str


def extract_task_id(response: TransportResponse) -> str | None:
    """Extract the task ID from a successful response.

    Handles both ``SendMessageResponse`` (oneof payload) and ``Task``
    (direct proto, returned by GetTask/CancelTask) for gRPC, as well
    as JSON-RPC and HTTP+JSON dict shapes.
    """
    raw = response.raw_response
    transport = response.transport

    if transport == "grpc":
        return _extract_grpc_task_id(raw)
    if transport == "jsonrpc":
        return _extract_jsonrpc_field(raw, "id")
    if transport == "http_json":
        return _extract_http_json_field(raw, "id")
    return None


def extract_context_id(response: TransportResponse) -> str | None:
    """Extract the context ID from a successful SendMessage response."""
    raw = response.raw_response
    transport = response.transport

    if transport == "grpc":
        return _extract_grpc_context_id(raw)
    if transport == "jsonrpc":
        return _extract_jsonrpc_field(raw, "contextId")
    if transport == "http_json":
        return _extract_http_json_field(raw, "contextId")
    return None


def create_task(client: BaseTransportClient) -> TaskInfo:
    """Create a task via ``send_message`` and return its identifiers.

    Calls ``pytest.skip`` if the task cannot be created (server error,
    missing task ID, etc.).
    """
    response = client.send_message(message=SAMPLE_MESSAGE)
    if not response.success:
        pytest.skip(f"send_message failed: {response.error}")

    task_id = extract_task_id(response)
    if not task_id:
        pytest.skip("Could not extract task ID from send_message response")

    context_id = extract_context_id(response)

    return TaskInfo(
        task_id=task_id,
        context_id=context_id,
        transport=response.transport,
    )


# ---------------------------------------------------------------------------
# Internal helpers — transport-specific extraction
# ---------------------------------------------------------------------------


def _extract_grpc_task_id(raw: Any) -> str | None:
    """Extract task ID from a gRPC protobuf response.

    Handles both ``SendMessageResponse`` (oneof with ``task`` field) and
    ``Task`` (returned directly by GetTask / CancelTask).
    """
    # SendMessageResponse has a "payload" oneof; Task proto does not.
    try:
        payload = raw.WhichOneof("payload")
        if payload == "task" and raw.task.id:
            return raw.task.id
    except (ValueError, AttributeError):
        pass
    # Task proto returned directly (GetTask, CancelTask)
    if hasattr(raw, "id") and raw.id:
        return raw.id
    return None


def _extract_grpc_context_id(raw: Any) -> str | None:
    """Extract context ID from a gRPC protobuf response.

    Handles both ``SendMessageResponse`` (oneof with ``task`` field) and
    ``Task`` (returned directly by GetTask / CancelTask).
    """
    try:
        payload = raw.WhichOneof("payload")
        if payload == "task" and raw.task.context_id:
            return raw.task.context_id
    except (ValueError, AttributeError):
        pass
    # Task proto returned directly (GetTask, CancelTask)
    if hasattr(raw, "context_id") and raw.context_id:
        return raw.context_id
    return None


def _extract_jsonrpc_field(raw: Any, field: str) -> str | None:
    """Extract a task field from a JSON-RPC 2.0 response dict."""
    if not isinstance(raw, dict):
        return None
    result = raw.get("result", {})
    if not isinstance(result, dict):
        return None
    # Task may be nested under "task" or at the top level of result
    task = result.get("task", result)
    if isinstance(task, dict):
        return task.get(field)
    return None


def _extract_http_json_field(raw: Any, field: str) -> str | None:
    """Extract a task field from an HTTP+JSON response dict."""
    if not isinstance(raw, dict):
        return None
    # Task may be nested under "task" or at the top level
    task = raw.get("task", raw)
    if isinstance(task, dict):
        return task.get(field)
    return None
