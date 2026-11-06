"""Unit tests for the INPUT_REQUIRED lifecycle send helpers.

The helper deliberately fails rather than skips when a blocking send answers
successfully without a task id: a bare Message cannot satisfy the
CORE-EXECUTION-MODE-001 input_required requirement, so converting that case to
a skip would hide the failure the test exists to catch.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from tests.compatibility.core_operations import test_task_input_required as mod


# The helper under test is module-private by design; these unit tests exist to
# pin the fail-versus-skip policy inside it.
send_input_required = mod._send_input_required  # noqa: SLF001


class _StubClient:
    def __init__(self, response: SimpleNamespace) -> None:
        self._response = response
        self.sent: list[dict[str, Any]] = []

    def send_message(self, *, message: dict[str, Any]) -> SimpleNamespace:
        self.sent.append(message)
        return self._response


def _response(**overrides: Any) -> SimpleNamespace:
    payload: dict[str, Any] = {
        "success": True,
        "error": None,
        "task_id": "task-1",
        "raw_response": {},
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_missing_task_id_fails_instead_of_skipping() -> None:
    """A successful response with no task id is a lifecycle failure."""
    client = _StubClient(_response(task_id=None))

    with pytest.raises(pytest.fail.Exception, match="without a task ID"):
        send_input_required(client)


def test_transport_failure_still_skips() -> None:
    """A transport-level failure leaves nothing to assert on, so it skips."""
    client = _StubClient(_response(success=False, error="connection refused", task_id=None))

    with pytest.raises(pytest.skip.Exception):
        send_input_required(client)


def test_task_id_is_returned_when_present() -> None:
    """A normal task response passes through unchanged."""
    client = _StubClient(_response(task_id="task-42"))

    assert send_input_required(client).task_id == "task-42"
