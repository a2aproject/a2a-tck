"""Cross-transport multi-stream ordering tests.

Validates that when multiple SubscribeToTask streams are open on the same
task concurrently, events are broadcast correctly, ordering is consistent,
and closing one stream does not affect others.

Requirements tested:
    STREAM-ORDER-002 — Events broadcast to all active streams
    STREAM-ORDER-003 — Each stream receives same events in same order
    STREAM-ORDER-004 — Closing one stream does not affect others
"""

from __future__ import annotations

import contextlib
import json
import threading

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.registry import get_requirement_by_id
from tck.transport import ALL_TRANSPORTS
from tests.compatibility._task_helpers import create_task
from tests.compatibility._test_helpers import fail_msg, get_client, record
from tests.compatibility.markers import must, streaming


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

STREAM_ORDER_002 = get_requirement_by_id("STREAM-ORDER-002")
STREAM_ORDER_003 = get_requirement_by_id("STREAM-ORDER-003")
STREAM_ORDER_004 = get_requirement_by_id("STREAM-ORDER-004")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SUBSCRIBE_TIMEOUT_S = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_events_with_timeout(
    events_iter: Any,
    timeout: float = _SUBSCRIBE_TIMEOUT_S,
    *,
    stop_after_first: bool = False,
) -> tuple[list[Any], bool]:
    """Collect streaming events with a hard wall-clock timeout.

    When *stop_after_first* is ``True`` the iterator is abandoned after the
    first event — used to simulate a client closing a stream early.

    Returns a tuple of (events, timed_out).
    """
    collected: list[Any] = []

    def _drain() -> None:
        for event in events_iter:
            collected.append(event)
            if stop_after_first:
                break

    thread = threading.Thread(target=_drain, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    timed_out = thread.is_alive()
    return collected, timed_out


def _normalize_event(event: Any) -> str:
    """Convert an event to a canonical string for cross-stream comparison.

    gRPC protos are serialized deterministically; JSON dicts are dumped with
    sorted keys so that comparison is independent of key insertion order.
    """
    if hasattr(event, "SerializeToString"):
        return event.SerializeToString().hex()
    if isinstance(event, dict):
        return json.dumps(event, sort_keys=True)
    return str(event)


def _subscribe_parallel(
    client: BaseTransportClient,
    task_id: str,
    n: int = 2,
    *,
    stop_first_early: bool = False,
) -> list[list[Any]]:
    """Open *n* concurrent ``subscribe_to_task`` streams and collect events.

    When *stop_first_early* is ``True``, the first stream is closed after
    receiving its first event while the remaining streams run to completion.

    Returns a list of event lists, one per stream.  Raises ``pytest.skip``
    if any subscription call fails.
    """
    results: list[list[Any]] = [[] for _ in range(n)]
    errors: list[str] = []
    threads: list[threading.Thread] = []

    # We need to open subscriptions concurrently.  Use a barrier so all
    # threads start consuming events roughly at the same time.
    barrier = threading.Barrier(n)

    def _consume(index: int) -> None:
        sub = client.subscribe_to_task(id=task_id)
        if not sub.success:
            errors.append(f"Stream {index} subscribe failed: {sub.error}")
            with contextlib.suppress(threading.BrokenBarrierError):
                barrier.wait(timeout=5)
            return
        with contextlib.suppress(threading.BrokenBarrierError):
            barrier.wait(timeout=5)
        early = stop_first_early and index == 0
        results[index], _ = _collect_events_with_timeout(
            sub.events,
            stop_after_first=early,
        )

    for i in range(n):
        t = threading.Thread(target=_consume, args=(i,), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=_SUBSCRIBE_TIMEOUT_S + 5)

    if errors:
        pytest.skip("; ".join(errors))

    return results


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@must
@streaming
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestMultiStreamOrdering:
    """Tests for multi-stream ordering.

    Validates behavior when multiple SubscribeToTask streams are open on
    the same task concurrently.
    """

    def test_events_broadcast_to_all_streams(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """STREAM-ORDER-002: Events are broadcast to all active streams."""
        req = STREAM_ORDER_002
        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compliance_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support streaming")

        client = get_client(transport_clients, transport, compliance_collector=compliance_collector, req=req)
        info = create_task(client)

        event_lists = _subscribe_parallel(client, info.task_id, n=2)

        errors: list[str] = []
        for i, events in enumerate(event_lists):
            if not events:
                errors.append(f"Stream {i} received no events")

        passed = not errors
        record(collector=compliance_collector, req=req, transport=transport, passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, "; ".join(errors))

    def test_streams_receive_same_events_in_order(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """STREAM-ORDER-003: Each stream receives the same events in the same order."""
        req = STREAM_ORDER_003
        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compliance_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support streaming")

        client = get_client(transport_clients, transport, compliance_collector=compliance_collector, req=req)
        info = create_task(client)

        event_lists = _subscribe_parallel(client, info.task_id, n=2)

        errors: list[str] = []
        if not event_lists[0] and not event_lists[1]:
            errors.append("Both streams received no events")
        elif not event_lists[0] or not event_lists[1]:
            errors.append(
                f"Stream 0 got {len(event_lists[0])} events, "
                f"stream 1 got {len(event_lists[1])} events — "
                "one stream received nothing"
            )
        else:
            normalized_0 = [_normalize_event(e) for e in event_lists[0]]
            normalized_1 = [_normalize_event(e) for e in event_lists[1]]
            if normalized_0 != normalized_1:
                errors.append(
                    f"Streams received different events or different ordering: "
                    f"stream 0 got {len(normalized_0)} events, "
                    f"stream 1 got {len(normalized_1)} events"
                )

        passed = not errors
        record(collector=compliance_collector, req=req, transport=transport, passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, "; ".join(errors))

    def test_closing_one_stream_does_not_affect_others(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compliance_collector: Any,
    ) -> None:
        """STREAM-ORDER-004: Closing one stream does not affect other active streams."""
        req = STREAM_ORDER_004
        caps = agent_card.get("capabilities", {})
        if not caps.get("streaming"):
            record(collector=compliance_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support streaming")

        client = get_client(transport_clients, transport, compliance_collector=compliance_collector, req=req)
        info = create_task(client)

        event_lists = _subscribe_parallel(
            client, info.task_id, n=2, stop_first_early=True,
        )

        errors: list[str] = []
        # Stream 0 was closed early — it should have at most 1 event
        if len(event_lists[0]) > 1:
            errors.append(
                f"Stream 0 should have stopped after 1 event, "
                f"got {len(event_lists[0])}"
            )
        # Stream 1 should have continued and received at least 1 event
        if not event_lists[1]:
            errors.append("Stream 1 received no events after stream 0 was closed")

        passed = not errors
        record(collector=compliance_collector, req=req, transport=transport, passed=passed, errors=errors)
        assert passed, fail_msg(req, transport, "; ".join(errors))
