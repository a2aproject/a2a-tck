"""Cross-transport task history tests.

Validates historyLength parameter semantics on GetTask and SendMessage.

Requirements tested:
    CORE-HIST-001 — historyLength=0 on GetTask omits history
    CORE-HIST-002 — History length does not exceed requested historyLength
    CORE-HIST-003 — historyLength=0 on SendMessage omits history
    CORE-HIST-004 — Agents may persist messages in task history
    CORE-HIST-005 — History messages are in chronological order
    CORE-HIST-006 — History content matches exchanged messages
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import tck_id
from tck.requirements.registry import get_requirement_by_id
from tck.transport import ALL_TRANSPORTS
from tck.validators.payload import extract_history, get_message_parts, get_part_text
from tests.compatibility._task_helpers import (
    HISTORY_MESSAGES,
    create_multiturn_task,
    create_multiturn_task_with_history,
    create_working_task,
)
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
CORE_HIST_005 = get_requirement_by_id("CORE-HIST-005")
CORE_HIST_006 = get_requirement_by_id("CORE-HIST-006")


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


# ---------------------------------------------------------------------------
# History ordering and content tests
# ---------------------------------------------------------------------------


_MIN_HISTORY_FOR_ORDERING = 2


def _extract_history_texts(history: list, transport: str) -> list[str]:
    """Extract text content from history messages across transports."""
    texts: list[str] = []
    for msg in history:
        for part in get_message_parts(msg, transport):
            text = get_part_text(part, transport)
            if text:
                texts.append(text)
    return texts


@should
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestHistoryOrdering:
    """Tests for history message ordering."""

    def test_history_messages_in_chronological_order(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """CORE-HIST-005: History messages should be in chronological order."""
        req = CORE_HIST_005
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_multiturn_task_with_history(client)

        response = client.get_task(id=info.task_id, history_length=10)

        errors: list[str] = []
        if not response.success:
            errors.append(f"GetTask failed: {response.error}")
        else:
            history = extract_history(response, transport)
            if len(history) < _MIN_HISTORY_FOR_ORDERING:
                errors.append(
                    f"Need at least 2 history messages to verify ordering, "
                    f"got {len(history)}"
                )
            else:
                texts = _extract_history_texts(history, transport)
                found = [t for t in texts if t in HISTORY_MESSAGES]
                if len(found) < _MIN_HISTORY_FOR_ORDERING:
                    errors.append(
                        f"Could not find enough known messages in history "
                        f"to verify ordering; found texts: {texts}"
                    )
                elif found != HISTORY_MESSAGES:
                    errors.append(
                        f"History messages not in chronological order: "
                        f"expected {HISTORY_MESSAGES}, got {found}"
                    )

        passed = not errors
        record(compatibility_collector, req, transport, passed=passed, errors=errors)
        if errors:
            pytest.xfail(fail_msg(req, transport, "; ".join(errors)))


@should
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestHistoryContent:
    """Tests for history message content fidelity."""

    def test_history_content_matches_sent_messages(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        compatibility_collector: Any,
    ) -> None:
        """CORE-HIST-006: History content should match exchanged messages."""
        req = CORE_HIST_006
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_multiturn_task_with_history(client)

        response = client.get_task(id=info.task_id, history_length=10)

        errors: list[str] = []
        if not response.success:
            errors.append(f"GetTask failed: {response.error}")
        else:
            history = extract_history(response, transport)
            if not history:
                errors.append(
                    "GetTask returned no history; cannot verify content"
                )
            else:
                texts = _extract_history_texts(history, transport)
                for expected_text in HISTORY_MESSAGES:
                    if expected_text not in texts:
                        errors.append(
                            f"Expected message {expected_text!r} not found "
                            f"in history; got: {texts}"
                        )

        passed = not errors
        record(compatibility_collector, req, transport, passed=passed, errors=errors)
        if errors:
            pytest.xfail(fail_msg(req, transport, "; ".join(errors)))
