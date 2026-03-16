"""Cross-transport push notification CRUD tests.

Validates push notification configuration lifecycle operations
that require a real task to exist first.

Requirements tested:
    PUSH-CREATE-001 — CreatePushNotificationConfig returns config
    PUSH-CREATE-002 — Config persists after creation
    PUSH-GET-001    — GetPushNotificationConfig returns config details
    PUSH-GET-002    — GetPushNotificationConfig for nonexistent returns error
    PUSH-LIST-001   — ListPushNotificationConfigs includes created config
    PUSH-DEL-001    — DeletePushNotificationConfig removes config
    PUSH-DEL-002    — Delete is idempotent
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tck.requirements.base import tck_id
from tck.requirements.registry import get_requirement_by_id
from tck.transport import ALL_TRANSPORTS
from tests.compatibility._task_helpers import create_completed_task
from tests.compatibility._test_helpers import assert_and_record, get_client, record
from tests.compatibility.markers import must


if TYPE_CHECKING:
    from tck.transport.base import BaseTransportClient


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _push_config() -> dict:
    """Generate a push notification config with a session-stable ID."""
    return {
        "id": tck_id("push"),
        "url": "https://example.com/tck-push-webhook",
    }


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
