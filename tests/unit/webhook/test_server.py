"""Tests for the webhook receiver server."""

from __future__ import annotations

import json

import httpx

from tck.webhook.server import WebhookReceiver, WebhookRequest


class TestWebhookRequest:
    """Tests for WebhookRequest dataclass."""

    def test_json_body_parsed(self) -> None:
        """JSON body is parsed automatically."""
        req = WebhookRequest(
            method="POST",
            path="/webhook",
            headers={},
            body=b'{"task": {"id": "123"}}',
        )
        assert req.json_body == {"task": {"id": "123"}}

    def test_invalid_json_body(self) -> None:
        """Non-JSON body leaves json_body as None."""
        req = WebhookRequest(
            method="POST",
            path="/webhook",
            headers={},
            body=b"not json",
        )
        assert req.json_body is None

    def test_empty_body(self) -> None:
        """Empty body leaves json_body as None."""
        req = WebhookRequest(
            method="POST",
            path="/webhook",
            headers={},
            body=b"",
        )
        assert req.json_body is None


class TestWebhookReceiver:
    """Tests for WebhookReceiver lifecycle and request capture."""

    def test_start_and_stop(self) -> None:
        """Server starts on a random port and stops cleanly."""
        receiver = WebhookReceiver()
        receiver.start()
        try:
            assert receiver.port > 0
        finally:
            receiver.stop()

    def test_url(self) -> None:
        """URL includes the correct host and port."""
        receiver = WebhookReceiver()
        receiver.start()
        try:
            assert receiver.url() == f"http://localhost:{receiver.port}/webhook"
            assert receiver.url("myhost") == f"http://myhost:{receiver.port}/webhook"
        finally:
            receiver.stop()

    def test_captures_post_request(self) -> None:
        """POST requests are captured with headers and body."""
        receiver = WebhookReceiver()
        receiver.start()
        try:
            payload = {"statusUpdate": {"state": "TASK_STATE_COMPLETED"}}
            httpx.post(
                receiver.url(),
                json=payload,
                headers={"Authorization": "Bearer test-token"},
            )
            req = receiver.wait_for_request(timeout=5)
            assert req is not None
            assert req.method == "POST"
            assert req.json_body == payload
            assert req.headers.get("Authorization") == "Bearer test-token"
        finally:
            receiver.stop()

    def test_wait_for_request_timeout(self) -> None:
        """wait_for_request returns None on timeout."""
        receiver = WebhookReceiver()
        receiver.start()
        try:
            req = receiver.wait_for_request(timeout=0.1)
            assert req is None
        finally:
            receiver.stop()

    def test_clear(self) -> None:
        """clear() discards captured requests."""
        receiver = WebhookReceiver()
        receiver.start()
        try:
            httpx.post(receiver.url(), json={"task": {}})
            assert receiver.wait_for_request(timeout=5) is not None

            receiver.clear()
            assert receiver.get_requests() == []
            assert receiver.wait_for_request(timeout=0.1) is None
        finally:
            receiver.stop()

    def test_get_requests_returns_copy(self) -> None:
        """get_requests() returns a snapshot, not a live reference."""
        receiver = WebhookReceiver()
        receiver.start()
        try:
            httpx.post(receiver.url(), json={"task": {}})
            receiver.wait_for_request(timeout=5)
            requests = receiver.get_requests()
            assert len(requests) == 1
            receiver.clear()
            assert len(requests) == 1
        finally:
            receiver.stop()

    def test_multiple_requests(self) -> None:
        """Multiple requests are all captured."""
        receiver = WebhookReceiver()
        receiver.start()
        num_requests = 3
        try:
            for i in range(num_requests):
                httpx.post(
                    receiver.url(),
                    content=json.dumps({"index": i}).encode(),
                    headers={"Content-Type": "application/json"},
                )
            import time
            time.sleep(0.2)
            requests = receiver.get_requests()
            assert len(requests) == num_requests
            for i, req in enumerate(requests):
                assert req.json_body["index"] == i
        finally:
            receiver.stop()
