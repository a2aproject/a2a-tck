"""Cross-transport task history tests.

Validates historyLength parameter semantics on GetTask and SendMessage.

Requirements tested:
    CORE-HIST-001 — historyLength=0 on GetTask omits history
    CORE-HIST-002 — History length does not exceed requested historyLength
    CORE-HIST-003 — historyLength=0 on SendMessage omits history
    CORE-HIST-004 — Agents may persist messages in task history
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import tck_id
from tck.requirements.registry import get_requirement_by_id
from tck.transport import ALL_TRANSPORTS
from tck.validators.payload import extract_history
from tests.compatibility._task_helpers import create_multiturn_task, create_working_task
from tests.compatibility._test_helpers import assert_and_record, fail_msg, get_client, record
from tests.compatibility.markers import may, must, should


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

CORE_HIST_001 = get_requirement_by_id("CORE-HIST-001")
CORE_HIST_002 = get_requirement_by_id("CORE-HIST-002")
CORE_HIST_003 = get_requirement_by_id("CORE-HIST-003")
CORE_HIST_004 = get_requirement_by_id("CORE-HIST-004")


# ---------------------------------------------------------------------------
# GetTask history tests
# ---------------------------------------------------------------------------


@should
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestHistoryLengthZeroGetTask:
    """Tests for historyLength=0 on GetTask."""

    def test_get_task_history_length_zero(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """CORE-HIST-001: GetTask with historyLength=0 returns no history."""
        req = CORE_HIST_001
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_multiturn_task(client)

        response = client.get_task(id=info.task_id, history_length=0)

        errors: list[str] = []
        if not response.success:
            errors.append(f"GetTask failed: {response.error}")
        else:
            history = extract_history(response, transport)
            if history:
                errors.append(
                    f"GetTask with historyLength=0 returned {len(history)} "
                    f"history message(s), expected none"
                )

        passed = not errors
        record(compatibility_collector, req, transport, passed=passed, errors=errors)
        if errors:
            pytest.xfail(fail_msg(req, transport, "; ".join(errors)))


@must
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestHistoryLengthLimit:
    """Tests for historyLength upper-bound enforcement."""

    def test_get_task_history_does_not_exceed_limit(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """CORE-HIST-002: GetTask history count must not exceed historyLength."""
        req = CORE_HIST_002
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_multiturn_task(client)

        requested_length = 1
        response = client.get_task(id=info.task_id, history_length=requested_length)

        errors: list[str] = []
        if not response.success:
            errors.append(f"GetTask failed: {response.error}")
        else:
            history = extract_history(response, transport)
            if len(history) > requested_length:
                errors.append(
                    f"GetTask with historyLength={requested_length} returned "
                    f"{len(history)} message(s), which exceeds the limit"
                )

        assert_and_record(compatibility_collector, req, transport, errors)


# ---------------------------------------------------------------------------
# SendMessage history tests
# ---------------------------------------------------------------------------


@should
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestHistoryLengthZeroSendMessage:
    """Tests for historyLength=0 on SendMessage."""

    def test_send_message_history_length_zero(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """CORE-HIST-003: SendMessage with historyLength=0 returns no history."""
        req = CORE_HIST_003
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)

        info = create_working_task(client)

        # Send follow-up with historyLength=0 to complete the task
        msg = {
            "role": "ROLE_USER",
            "parts": [{"text": "Follow-up with no history"}],
            "messageId": tck_id("complete-task"),
            "taskId": info.task_id,
        }
        response = client.send_message(
            message=msg,
            configuration={"historyLength": 0},
        )

        errors: list[str] = []
        if not response.success:
            errors.append(f"SendMessage failed: {response.error}")
        else:
            history = extract_history(response, transport)
            if history:
                errors.append(
                    f"SendMessage with historyLength=0 returned {len(history)} "
                    f"history message(s), expected none"
                )

        passed = not errors
        record(compatibility_collector, req, transport, passed=passed, errors=errors)
        if errors:
            pytest.xfail(fail_msg(req, transport, "; ".join(errors)))


# ---------------------------------------------------------------------------
# History persistence tests
# ---------------------------------------------------------------------------


@may
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestHistoryPersistence:
    """Tests for agent history persistence."""

    def test_get_task_returns_history(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """CORE-HIST-004: GetTask with historyLength>0 may return persisted messages."""
        req = CORE_HIST_004
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_multiturn_task(client)

        response = client.get_task(id=info.task_id, history_length=10)

        errors: list[str] = []
        if not response.success:
            errors.append(f"GetTask failed: {response.error}")
        else:
            history = extract_history(response, transport)
            if not history:
                errors.append(
                    "GetTask with historyLength=10 returned no history; "
                    "agent does not persist messages in task history"
                )

        passed = not errors
        record(compatibility_collector, req, transport, passed=passed, errors=errors)
        if errors:
            pytest.xfail(fail_msg(req, transport, "; ".join(errors)))
