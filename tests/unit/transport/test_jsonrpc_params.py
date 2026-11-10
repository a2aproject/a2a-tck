"""Unit tests for JSON-RPC request params (issue #264).

A2A Section 5.5 requires camelCase field names in every JSON serialization,
so the JSON-RPC client must not send the Python keyword names on the wire.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.transport.jsonrpc_client import JsonRpcClient


if TYPE_CHECKING:
    from collections.abc import Callable


_URL = "https://example.com/tck-push-webhook"
_TIMESTAMP = "2026-01-01T00:00:00Z"


@pytest.mark.parametrize(
    ("call", "expected"),
    [
        pytest.param(
            lambda client: client.create_push_notification_config("task-1", {"id": "cfg-1", "url": _URL}),
            {"taskId": "task-1", "id": "cfg-1", "url": _URL},
            id="create_push_notification_config",
        ),
        pytest.param(
            lambda client: client.get_push_notification_config("task-1", "cfg-1"),
            {"taskId": "task-1", "id": "cfg-1"},
            id="get_push_notification_config",
        ),
        pytest.param(
            lambda client: client.list_push_notification_configs("task-1", page_size=5, page_token="next"),
            {"taskId": "task-1", "pageSize": 5, "pageToken": "next"},
            id="list_push_notification_configs",
        ),
        pytest.param(
            lambda client: client.delete_push_notification_config("task-1", "cfg-1"),
            {"taskId": "task-1", "id": "cfg-1"},
            id="delete_push_notification_config",
        ),
        pytest.param(
            lambda client: client.list_tasks(
                "ctx-1",
                page_size=5,
                page_token="next",
                history_length=2,
                status_timestamp_after=_TIMESTAMP,
                include_artifacts=True,
            ),
            {
                "contextId": "ctx-1",
                "pageSize": 5,
                "pageToken": "next",
                "historyLength": 2,
                "statusTimestampAfter": _TIMESTAMP,
                "includeArtifacts": True,
            },
            id="list_tasks",
        ),
    ],
)
def test_params_use_camel_case_field_names(
    call: Callable[[JsonRpcClient], object],
    expected: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each method sends its params under the spec's camelCase names."""
    sent: list[dict[str, Any]] = []
    monkeypatch.setattr(JsonRpcClient, "_call", lambda _self, _method, params: sent.append(params))

    client = JsonRpcClient("http://localhost:9999")
    try:
        call(client)
    finally:
        client.close()

    assert sent == [expected]
