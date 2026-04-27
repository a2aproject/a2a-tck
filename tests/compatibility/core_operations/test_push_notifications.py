"""Cross-transport push notification tests.

Validates push notification configuration lifecycle operations
and webhook delivery behavior.

Requirements tested:
    PUSH-CREATE-001  — CreatePushNotificationConfig returns config
    PUSH-CREATE-002  — Config persists after creation
    PUSH-GET-001     — GetPushNotificationConfig returns config details
    PUSH-GET-002     — GetPushNotificationConfig for nonexistent returns error
    PUSH-LIST-001    — ListPushNotificationConfigs includes created config
    PUSH-DEL-001     — DeletePushNotificationConfig removes config
    PUSH-DEL-002     — Delete is idempotent
    PUSH-DELIVER-001 — Agent includes auth in webhook requests
    PUSH-DELIVER-002 — Agent attempts delivery at least once
    PUSH-DELIVER-003 — Webhook payload uses StreamResponse format
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import tck_id
from tck.requirements.registry import get_requirement_by_id
from tck.transport import ALL_TRANSPORTS
from tests.compatibility._task_helpers import create_completed_task, create_working_task
from tests.compatibility._test_helpers import assert_and_record, get_client, record
from tests.compatibility.markers import must


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient
    from tck.validators.json_schema import JSONSchemaValidator
    from tck.webhook.server import WebhookReceiver


# ---------------------------------------------------------------------------
# Requirement lookups
# ---------------------------------------------------------------------------

PUSH_CREATE_001 = get_requirement_by_id("PUSH-CREATE-001")
PUSH_CREATE_002 = get_requirement_by_id("PUSH-CREATE-002")
PUSH_GET_001 = get_requirement_by_id("PUSH-GET-001")
PUSH_GET_002 = get_requirement_by_id("PUSH-GET-002")
PUSH_LIST_001 = get_requirement_by_id("PUSH-LIST-001")
PUSH_DEL_001 = get_requirement_by_id("PUSH-DEL-001")
PUSH_DEL_002 = get_requirement_by_id("PUSH-DEL-002")
PUSH_DELIVER_001 = get_requirement_by_id("PUSH-DELIVER-001")
PUSH_DELIVER_002 = get_requirement_by_id("PUSH-DELIVER-002")
PUSH_DELIVER_003 = get_requirement_by_id("PUSH-DELIVER-003")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_AUTH_SCHEME = "Bearer"
_AUTH_CREDENTIALS = f"tck-test-token-{tck_id('auth')}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _push_config() -> dict:
    """Generate a push notification config with a session-stable ID."""
    return {
        "id": tck_id("push"),
        "url": "https://example.com/tck-push-webhook",
    }


def _push_config_with_webhook(webhook_url: str) -> dict:
    """Generate a push notification config pointing at the TCK webhook receiver."""
    return {
        "id": tck_id("push"),
        "url": webhook_url,
        "authentication": {
            "scheme": _AUTH_SCHEME,
            "credentials": _AUTH_CREDENTIALS,
        },
    }


def _trigger_state_change(client: Any) -> tuple[str, str | None]:
    """Create a task in input_required state, then complete it.

    Returns (task_id, context_id) so the caller can register a push
    config between creation and completion.  This helper only does the
    first step (creating the working task).
    """
    info = create_working_task(client)
    return info.task_id, info.context_id


# ---------------------------------------------------------------------------
# Push notification CRUD tests
# ---------------------------------------------------------------------------


@must
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestPushNotificationCrud:
    """Tests for push notification configuration CRUD operations."""

    def test_create_push_config(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """PUSH-CREATE-001: CreatePushNotificationConfig returns the config."""
        req = PUSH_CREATE_001
        caps = agent_card.get("capabilities", {})
        if not caps.get("pushNotifications"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support push notifications")
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_completed_task(client)
        config = _push_config()

        response = client.create_push_notification_config(
            task_id=info.task_id,
            config=config,
        )

        errors: list[str] = []
        if not response.success:
            errors.append(f"CreatePushNotificationConfig failed: {response.error}")

        assert_and_record(compatibility_collector, req, transport, errors)

    def test_config_persists(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """PUSH-CREATE-002: Config persists and can be retrieved after creation."""
        req = PUSH_CREATE_002
        caps = agent_card.get("capabilities", {})
        if not caps.get("pushNotifications"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support push notifications")
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_completed_task(client)
        config = _push_config()

        create_resp = client.create_push_notification_config(
            task_id=info.task_id,
            config=config,
        )
        if not create_resp.success:
            pytest.skip(f"CreatePushNotificationConfig failed: {create_resp.error}")

        get_resp = client.get_push_notification_config(
            task_id=info.task_id,
            id=config["id"],
        )

        errors: list[str] = []
        if not get_resp.success:
            errors.append(
                f"GetPushNotificationConfig failed after creation: {get_resp.error}"
            )

        assert_and_record(compatibility_collector, req, transport, errors)

    def test_get_push_config(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """PUSH-GET-001: GetPushNotificationConfig returns config details."""
        req = PUSH_GET_001
        caps = agent_card.get("capabilities", {})
        if not caps.get("pushNotifications"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support push notifications")
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_completed_task(client)
        config = _push_config()

        create_resp = client.create_push_notification_config(
            task_id=info.task_id,
            config=config,
        )
        if not create_resp.success:
            pytest.skip(f"CreatePushNotificationConfig failed: {create_resp.error}")

        response = client.get_push_notification_config(
            task_id=info.task_id,
            id=config["id"],
        )

        errors: list[str] = []
        if not response.success:
            errors.append(f"GetPushNotificationConfig failed: {response.error}")

        assert_and_record(compatibility_collector, req, transport, errors)

    def test_get_nonexistent_config_returns_error(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """PUSH-GET-002: GetPushNotificationConfig with nonexistent ID returns error."""
        req = PUSH_GET_002
        caps = agent_card.get("capabilities", {})
        if not caps.get("pushNotifications"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support push notifications")
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_completed_task(client)

        response = client.get_push_notification_config(
            task_id=info.task_id,
            id=tck_id("nonexistent"),
        )

        errors: list[str] = []
        if response.success:
            errors.append(
                "GetPushNotificationConfig with nonexistent config ID should "
                "return an error, but succeeded"
            )

        assert_and_record(compatibility_collector, req, transport, errors)

    def test_list_push_configs(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """PUSH-LIST-001: ListPushNotificationConfigs includes the created config."""
        req = PUSH_LIST_001
        caps = agent_card.get("capabilities", {})
        if not caps.get("pushNotifications"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support push notifications")
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_completed_task(client)
        config = _push_config()

        create_resp = client.create_push_notification_config(
            task_id=info.task_id,
            config=config,
        )
        if not create_resp.success:
            pytest.skip(f"CreatePushNotificationConfig failed: {create_resp.error}")

        response = client.list_push_notification_configs(task_id=info.task_id)

        errors: list[str] = []
        if not response.success:
            errors.append(f"ListPushNotificationConfigs failed: {response.error}")

        assert_and_record(compatibility_collector, req, transport, errors)

    def test_delete_push_config(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """PUSH-DEL-001: DeletePushNotificationConfig removes the config."""
        req = PUSH_DEL_001
        caps = agent_card.get("capabilities", {})
        if not caps.get("pushNotifications"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support push notifications")
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_completed_task(client)
        config = _push_config()

        create_resp = client.create_push_notification_config(
            task_id=info.task_id,
            config=config,
        )
        if not create_resp.success:
            pytest.skip(f"CreatePushNotificationConfig failed: {create_resp.error}")

        # Delete
        del_resp = client.delete_push_notification_config(
            task_id=info.task_id,
            id=config["id"],
        )

        errors: list[str] = []
        if not del_resp.success:
            errors.append(f"DeletePushNotificationConfig failed: {del_resp.error}")
        else:
            # Verify it is gone
            get_resp = client.get_push_notification_config(
                task_id=info.task_id,
                id=config["id"],
            )
            if get_resp.success:
                errors.append(
                    "Config still exists after deletion — "
                    "GetPushNotificationConfig should return an error"
                )

        assert_and_record(compatibility_collector, req, transport, errors)

    def test_delete_is_idempotent(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
    ) -> None:
        """PUSH-DEL-002: Deleting an already-deleted config does not error."""
        req = PUSH_DEL_002
        caps = agent_card.get("capabilities", {})
        if not caps.get("pushNotifications"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support push notifications")
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)
        info = create_completed_task(client)
        config = _push_config()

        create_resp = client.create_push_notification_config(
            task_id=info.task_id,
            config=config,
        )
        if not create_resp.success:
            pytest.skip(f"CreatePushNotificationConfig failed: {create_resp.error}")

        # Delete twice
        client.delete_push_notification_config(
            task_id=info.task_id,
            id=config["id"],
        )
        second_del = client.delete_push_notification_config(
            task_id=info.task_id,
            id=config["id"],
        )

        errors: list[str] = []
        if not second_del.success:
            errors.append(
                f"Second delete should be idempotent (no error), "
                f"but returned: {second_del.error}"
            )

        assert_and_record(compatibility_collector, req, transport, errors)


# ---------------------------------------------------------------------------
# Push notification delivery tests
# ---------------------------------------------------------------------------

_DELIVERY_TIMEOUT_S = 15


def _setup_push_and_trigger(
    client: Any,
    webhook_url: str,
) -> tuple[dict, str]:
    """Create a task with inline push config, then trigger a state change.

    Sends the push notification config alongside the initial SendMessage
    via the ``configuration.pushNotificationConfig`` field, then sends a
    follow-up message to complete the task and trigger webhook delivery.

    Returns (push_config, task_id).
    """
    config = _push_config_with_webhook(webhook_url)

    message: dict[str, Any] = {
        "role": "ROLE_USER",
        "parts": [{"text": "TCK prerequisite task creation"}],
        "messageId": tck_id("input-required"),
    }
    configuration = {"taskPushNotificationConfig": config}
    response = client.send_message(message=message, configuration=configuration)
    if not response.success:
        pytest.skip(f"send_message failed: {response.error}")

    task_id = response.task_id
    if not task_id:
        pytest.skip("Could not extract task ID from send_message response")

    followup: dict[str, Any] = {
        "role": "ROLE_USER",
        "parts": [{"text": "TCK trigger push notification delivery"}],
        "messageId": tck_id("complete-task"),
        "taskId": task_id,
    }
    response = client.send_message(message=followup)
    if not response.success:
        pytest.skip(f"Follow-up send_message failed: {response.error}")

    return config, task_id


@must
@pytest.mark.parametrize("transport", ALL_TRANSPORTS)
class TestPushNotificationDelivery:
    """Tests for push notification webhook delivery."""

    def test_delivery_includes_auth(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
        webhook_receiver: WebhookReceiver,
        webhook_host: str,
    ) -> None:
        """PUSH-DELIVER-001: Agent includes auth credentials in webhook requests."""
        req = PUSH_DELIVER_001
        caps = agent_card.get("capabilities", {})
        if not caps.get("pushNotifications"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support push notifications")
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)

        webhook_receiver.clear()
        _setup_push_and_trigger(client, webhook_receiver.url(webhook_host))
        webhook_req = webhook_receiver.wait_for_request(timeout=_DELIVERY_TIMEOUT_S)

        errors: list[str] = []
        if webhook_req is None:
            errors.append("No webhook request received within timeout")
        else:
            auth_header = webhook_req.headers.get("authorization", "")
            expected = f"{_AUTH_SCHEME} {_AUTH_CREDENTIALS}"
            if auth_header != expected:
                errors.append(
                    f"Expected Authorization header '{expected}', "
                    f"got '{auth_header}'"
                )

        assert_and_record(compatibility_collector, req, transport, errors)

    def test_delivery_at_least_once(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
        webhook_receiver: WebhookReceiver,
        webhook_host: str,
    ) -> None:
        """PUSH-DELIVER-002: Agent attempts delivery at least once per webhook."""
        req = PUSH_DELIVER_002
        caps = agent_card.get("capabilities", {})
        if not caps.get("pushNotifications"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support push notifications")
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)

        webhook_receiver.clear()
        _setup_push_and_trigger(client, webhook_receiver.url(webhook_host))
        webhook_req = webhook_receiver.wait_for_request(timeout=_DELIVERY_TIMEOUT_S)

        errors: list[str] = []
        if webhook_req is None:
            errors.append(
                "No webhook delivery received — agent MUST attempt "
                "at least one delivery per configured webhook"
            )

        assert_and_record(compatibility_collector, req, transport, errors)

    def test_delivery_payload_format(
        self,
        transport: str,
        transport_clients: dict[str, BaseTransportClient],
        agent_card: dict[str, Any],
        compatibility_collector: Any,
        webhook_receiver: WebhookReceiver,
        webhook_host: str,
        validators: dict[str, Any],
    ) -> None:
        """PUSH-DELIVER-003: Webhook payload uses StreamResponse format."""
        req = PUSH_DELIVER_003
        caps = agent_card.get("capabilities", {})
        if not caps.get("pushNotifications"):
            record(collector=compatibility_collector, req=req, transport=transport, passed=False, skipped=True)
            pytest.skip("Agent does not support push notifications")
        client = get_client(transport_clients, transport, compatibility_collector=compatibility_collector, req=req)

        webhook_receiver.clear()
        _setup_push_and_trigger(client, webhook_receiver.url(webhook_host))
        webhook_req = webhook_receiver.wait_for_request(timeout=_DELIVERY_TIMEOUT_S)

        errors: list[str] = []
        if webhook_req is None:
            errors.append("No webhook request received within timeout")
        elif webhook_req.json_body is None:
            errors.append(
                f"Webhook body is not valid JSON: {webhook_req.body!r}"
            )
        else:
            json_validator: JSONSchemaValidator = validators["http_json"]
            result = json_validator.validate(webhook_req.json_body, "Stream Response")
            if not result.valid:
                errors.extend(result.errors)

        assert_and_record(compatibility_collector, req, transport, errors)
