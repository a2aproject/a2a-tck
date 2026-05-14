import logging
import uuid

import pytest

from tck import agent_card_utils
from tests.markers import optional_capability
from tests.capability_validator import CapabilityValidator
from tests.utils import transport_helpers

logger = logging.getLogger(__name__)

_DELIVERY_TIMEOUT_S = 15
_AUTH_SCHEME = "Bearer"
_AUTH_CREDENTIALS = "tck-test-token-" + str(uuid.uuid4())
_NOTIFICATION_TOKEN = "tck-notification-token-" + str(uuid.uuid4())


def _create_task_with_push_config(sut_client, webhook_url, config):
    """Create a task and configure push notifications pointing at the webhook.

    Returns the task ID.
    """
    message_params = {
        "message": {
            "messageId": "test-push-delivery-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [{"kind": "text", "text": "Task for push notification delivery test"}],
            "kind": "message",
        }
    }
    resp = transport_helpers.transport_send_message(sut_client, message_params)
    assert transport_helpers.is_json_rpc_success_response(resp), (
        f"Failed to create task: {resp}"
    )
    task_id = resp["result"]["id"]

    push_config = {"url": webhook_url}
    push_config.update(config)
    set_resp = transport_helpers.transport_set_push_notification_config(
        sut_client, task_id, push_config
    )
    assert transport_helpers.is_json_rpc_success_response(set_resp), (
        f"Failed to set push notification config: {set_resp}"
    )

    return task_id


def _trigger_state_change(sut_client, task_id):
    """Send a follow-up message to trigger a task state change."""
    message_params = {
        "message": {
            "messageId": "test-push-trigger-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [{"kind": "text", "text": "Complete the task to trigger push notification"}],
            "kind": "message",
            "taskId": task_id,
        }
    }
    resp = transport_helpers.transport_send_message(sut_client, message_params)
    assert transport_helpers.is_json_rpc_success_response(resp), (
        f"Failed to send follow-up message: {resp}"
    )


def _setup_and_wait(sut_client, webhook_receiver, webhook_host, config):
    """Create task with push config, trigger state change, wait for webhook."""
    webhook_receiver.clear()
    webhook_url = webhook_receiver.url(webhook_host)
    task_id = _create_task_with_push_config(sut_client, webhook_url, config)
    _trigger_state_change(sut_client, task_id)
    return webhook_receiver.wait_for_request(timeout=_DELIVERY_TIMEOUT_S)


@optional_capability
def test_push_notification_delivery_received(
    sut_client, agent_card_data, webhook_receiver, webhook_host
):
    """
    CONDITIONAL MANDATORY: A2A Specification Section 9.5 - Push Notification Delivery

    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing

    Test validates that the SUT delivers at least one webhook request when
    a task state changes after push notification config has been set.
    """
    validator = CapabilityValidator(agent_card_data)
    if not validator.is_capability_declared("pushNotifications"):
        pytest.skip("Push notifications capability not declared - test not applicable")

    config = {
        "token": _NOTIFICATION_TOKEN,
    }
    req = _setup_and_wait(sut_client, webhook_receiver, webhook_host, config)
    assert req is not None, (
        "No webhook delivery received within timeout - agent MUST attempt "
        "at least one delivery per configured webhook"
    )


@optional_capability
def test_push_notification_delivery_token_header(
    sut_client, agent_card_data, webhook_receiver, webhook_host
):
    """
    CONDITIONAL MANDATORY: A2A Specification Section 9.5 - Push Notification Token

    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing

    Test validates that the SUT includes the configured token in the
    X-A2A-Notification-Token header of webhook requests.
    """
    validator = CapabilityValidator(agent_card_data)
    if not validator.is_capability_declared("pushNotifications"):
        pytest.skip("Push notifications capability not declared - test not applicable")

    config = {
        "token": _NOTIFICATION_TOKEN,
    }
    req = _setup_and_wait(sut_client, webhook_receiver, webhook_host, config)
    assert req is not None, "No webhook delivery received within timeout"

    token_header = req.headers.get("x-a2a-notification-token", "")
    assert token_header == _NOTIFICATION_TOKEN, (
        f"Expected X-A2A-Notification-Token header '{_NOTIFICATION_TOKEN}', "
        f"got '{token_header}'"
    )


@optional_capability
def test_push_notification_delivery_auth_header(
    sut_client, agent_card_data, webhook_receiver, webhook_host
):
    """
    CONDITIONAL MANDATORY: A2A Specification Section 9.5 - Push Notification Authentication

    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing

    Test validates that the SUT includes the configured authentication
    credentials in the Authorization header of webhook requests.
    """
    validator = CapabilityValidator(agent_card_data)
    if not validator.is_capability_declared("pushNotifications"):
        pytest.skip("Push notifications capability not declared - test not applicable")

    config = {
        "authentication": {
            "schemes": [_AUTH_SCHEME],
            "credentials": _AUTH_CREDENTIALS,
        },
    }
    req = _setup_and_wait(sut_client, webhook_receiver, webhook_host, config)
    assert req is not None, "No webhook delivery received within timeout"

    auth_header = req.headers.get("authorization", "")
    expected = f"{_AUTH_SCHEME} {_AUTH_CREDENTIALS}"
    assert auth_header == expected, (
        f"Expected Authorization header '{expected}', got '{auth_header}'"
    )


@optional_capability
def test_push_notification_delivery_payload_is_task(
    sut_client, agent_card_data, webhook_receiver, webhook_host
):
    """
    CONDITIONAL MANDATORY: A2A Specification Section 9.5 - Push Notification Payload

    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing

    Test validates that the webhook payload is a v0.3 Task object with
    required fields (id, status, kind="task"), not a StreamResponse wrapper.
    """
    validator = CapabilityValidator(agent_card_data)
    if not validator.is_capability_declared("pushNotifications"):
        pytest.skip("Push notifications capability not declared - test not applicable")

    config = {
        "token": _NOTIFICATION_TOKEN,
    }
    req = _setup_and_wait(sut_client, webhook_receiver, webhook_host, config)
    assert req is not None, "No webhook delivery received within timeout"
    assert req.json_body is not None, (
        f"Webhook body is not valid JSON: {req.body!r}"
    )

    payload = req.json_body

    # v0.3 payload MUST be a Task object directly (not wrapped in StreamResponse)
    assert "id" in payload, (
        f"Webhook payload missing 'id' field. Got keys: {list(payload.keys())}"
    )
    assert "status" in payload, (
        f"Webhook payload missing 'status' field. Got keys: {list(payload.keys())}"
    )
    assert payload.get("kind") == "task", (
        f"Webhook payload 'kind' should be 'task', got: {payload.get('kind')}"
    )

    # Verify this is NOT a StreamResponse (1.0 format)
    stream_response_keys = {"task", "message", "statusUpdate", "artifactUpdate"}
    if set(payload.keys()) & stream_response_keys == set(payload.keys()) and len(payload) == 1:
        pytest.fail(
            "Webhook payload appears to be a StreamResponse wrapper (v1.0 format). "
            "v0.3 expects a plain Task object as the payload."
        )

    # Validate status structure
    status = payload["status"]
    assert isinstance(status, dict), f"Task status should be an object, got: {type(status)}"
    assert "state" in status, f"Task status missing 'state' field. Got: {status}"
