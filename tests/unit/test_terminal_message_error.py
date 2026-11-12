"""Regression coverage for CORE-SEND-002's expected-error assertion."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from tck.transport.jsonrpc_client import JsonRpcResponse
from tests.compatibility.core_operations.test_task_lifecycle import TestMultiTurn as _LifecycleTests


@pytest.mark.parametrize(
    ("code", "success", "expected_pass"),
    [
        (-32004, False, True),
        (-32603, False, False),
        (-32001, False, False),
        (None, False, False),
        (None, True, False),
    ],
)
def test_terminal_message_requires_expected_error(
    code: int | None, success: bool, expected_pass: bool,
) -> None:
    """Wrong errors must fail compatibility even though the send was rejected."""
    completed = JsonRpcResponse(
        transport="jsonrpc",
        success=True,
        raw_response={
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"task": {
                "id": "task-1",
                "contextId": "context-1",
                "status": {"state": "TASK_STATE_COMPLETED"},
            }},
        },
    )
    raw = {"jsonrpc": "2.0", "id": 2}
    if success:
        raw["result"] = {"task": {"id": "task-1"}}
    else:
        raw["error"] = {"message": "Controlled test response"}
        if code is not None:
            raw["error"]["code"] = code
    followup = JsonRpcResponse(transport="jsonrpc", success=success, raw_response=raw)
    client, collector = Mock(), Mock()
    client.transport = "jsonrpc"
    responses = [completed, followup]
    client.send_message.side_effect = responses
    client.get_task.return_value = completed

    if expected_pass:
        _LifecycleTests().test_send_message_to_terminal_task("jsonrpc", {"jsonrpc": client}, collector)
    else:
        with pytest.raises(AssertionError, match="CORE-SEND-002"):
            _LifecycleTests().test_send_message_to_terminal_task("jsonrpc", {"jsonrpc": client}, collector)

    collector.record.assert_called_once()
    recorded = collector.record.call_args.kwargs
    assert recorded["requirement_id"] == "CORE-SEND-002"
    assert recorded["passed"] is expected_pass
    assert client.send_message.call_count == len(responses)
