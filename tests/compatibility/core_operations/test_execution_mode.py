"""Execution-mode (blocking vs non-blocking) behaviour tests.

The generic requirement runner only checks that a ``SendMessage`` response is
well-formed, so a server that ignores the ``returnImmediately`` configuration
flag still passes it.  These tests drive the ``tck-delayed-complete`` SUT
scenario, which holds the task in a non-terminal ``working`` state for a bounded
delay before completing, so blocking and non-blocking sends produce observably
different responses.

Requirements tested:
    CORE-EXECUTION-MODE-001: blocking send waits for a terminal/interrupted state
    CORE-EXECUTION-MODE-002: non-blocking send returns before the task completes
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import tck_id
from tck.requirements.registry import get_requirement_by_id
from tck.transport import ALL_TRANSPORTS
from tests.compatibility._test_helpers import (
    assert_and_record,
    get_client,
    is_terminal_status,
)
from tests.compatibility.markers import must


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

CORE_EXECUTION_MODE_001 = get_requirement_by_id("CORE-EXECUTION-MODE-001")
CORE_EXECUTION_MODE_002 = get_requirement_by_id("CORE-EXECUTION-MODE-002")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _delayed_message() -> dict[str, Any]:
    """Build a message that routes to the delayed-complete SUT scenario."""
    return {
        "role": "ROLE_USER",
        "parts": [{"text": "Execution-mode probe"}],
        "messageId": tck_id("delayed-complete"),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@must
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestExecutionMode:
    """Tests for blocking vs non-blocking SendMessage behaviour."""

    def test_blocking_waits_for_terminal_state(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """CORE-EXECUTION-MODE-001: a blocking send waits for a terminal state.

        With ``returnImmediately`` false the server must not return until the
        task reaches a terminal (or interrupted) state.  A server that ignores
        the flag returns while the task is still ``working`` and fails here.
        """
        req = CORE_EXECUTION_MODE_001
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)

        response = client.send_message(
            message=_delayed_message(),
            configuration={"returnImmediately": False},
        )

        errors: list[str] = []
        if not response.success:
            errors.append(f"Blocking send_message failed: {response.error}")
        elif not is_terminal_status(response, transport):
            errors.append(
                "Blocking send_message (returnImmediately=false) returned before "
                "the task reached a terminal state"
            )

        assert_and_record(compatibility_collector, req, transport, errors)

    def test_non_blocking_returns_before_completion(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """CORE-EXECUTION-MODE-002: a non-blocking send returns immediately.

        With ``returnImmediately`` true the server must return while the task
        is still in progress.  A server that ignores the flag blocks until the
        task is terminal and fails here.
        """
        req = CORE_EXECUTION_MODE_002
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)

        response = client.send_message(
            message=_delayed_message(),
            configuration={"returnImmediately": True},
        )

        errors: list[str] = []
        if not response.success:
            errors.append(f"Non-blocking send_message failed: {response.error}")
        elif is_terminal_status(response, transport):
            errors.append(
                "Non-blocking send_message (returnImmediately=true) did not return "
                "until the task reached a terminal state"
            )

        assert_and_record(compatibility_collector, req, transport, errors)
