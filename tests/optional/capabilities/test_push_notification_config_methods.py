import logging
import uuid

import pytest

from tck import agent_card_utils, message_utils
from tck.sut_client import SUTClient
from tests.markers import optional_capability
from tests.capability_validator import CapabilityValidator

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()

@pytest.fixture
def created_task_id(sut_client):
    # Create a task using message/send and return its id
    params = {
        "message": {
            "messageId": "test-push-notification-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {"kind": "text", "text": "Task for push notification config test"}
            ],
            "kind": "message"
        }
    }
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = sut_client.send_json_rpc(**req)
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    return resp["result"]["id"]

# Helper function to check push notification support
def has_push_notification_support(agent_card_data):
    """Check if the SUT supports push notifications based on Agent Card data."""
    if agent_card_data is None:
        logger.warning("Agent Card data is None, assuming push notifications are not supported")
        return False
    
    return agent_card_utils.get_capability_push_notifications(agent_card_data)

@optional_capability
def test_set_push_notification_config(sut_client, created_task_id, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §9.1 - Push Notification Configuration
    
    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing
            
    Test validates the tasks/pushNotificationConfig/set method for setting
    push notification configurations on tasks.
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('pushNotifications'):
        pytest.skip("Push notifications capability not declared - test not applicable")
    
    config_params = {
        "taskId": created_task_id,
        "config": {
            "type": "webhook",
            "url": "https://example.com/webhook"
        }
    }
    req = message_utils.make_json_rpc_request("tasks/pushNotificationConfig/set", params=config_params)
    resp = sut_client.send_json_rpc(**req)
    
    # Since push notifications capability is declared, this MUST work
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"]), \
        "Push notifications capability declared but set config failed"
    
    result = resp["result"]
    assert result["type"] == "webhook", "Push notification config type not echoed correctly"
    assert result["url"] == "https://example.com/webhook", "Push notification config URL not echoed correctly"

@optional_capability
def test_get_push_notification_config(sut_client, created_task_id, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §9.1 - Push Notification Configuration Retrieval
    
    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing
            
    Test validates the tasks/pushNotificationConfig/get method for retrieving
    push notification configurations from tasks.
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('pushNotifications'):
        pytest.skip("Push notifications capability not declared - test not applicable")
    
    params = {"taskId": created_task_id}
    req = message_utils.make_json_rpc_request("tasks/pushNotificationConfig/get", params=params)
    resp = sut_client.send_json_rpc(**req)
    
    # Since push notifications capability is declared, this MUST work
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"]), \
        "Push notifications capability declared but get config failed"
    
    result = resp["result"]
    assert "type" in result, "Push notification config must have type field"

@optional_capability
def test_set_push_notification_config_nonexistent(sut_client, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §9.1 - Push Notification Error Handling
    
    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing
            
    Test validates proper error handling for push notification config operations
    on non-existent tasks.
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('pushNotifications'):
        pytest.skip("Push notifications capability not declared - test not applicable")
    
    config_params = {
        "taskId": "nonexistent-task-id",
        "config": {
            "type": "webhook",
            "url": "https://example.com/webhook"
        }
    }
    req = message_utils.make_json_rpc_request("tasks/pushNotificationConfig/set", params=config_params)
    resp = sut_client.send_json_rpc(**req)
    
    # Should return proper JSON-RPC error for non-existent task
    assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"]), \
        "Push notifications capability declared but invalid task ID not properly rejected"
    
    # Should indicate task not found
    error_message = resp["error"]["message"].lower()
    assert "not found" in error_message or "task" in error_message, \
        "Error message should indicate task was not found"

@optional_capability
def test_get_push_notification_config_nonexistent(sut_client, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §9.1 - Push Notification Error Handling
    
    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing
            
    Test validates proper error handling for push notification config retrieval
    on non-existent tasks.
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('pushNotifications'):
        pytest.skip("Push notifications capability not declared - test not applicable")

    params = {"taskId": "nonexistent-task-id"}
    req = message_utils.make_json_rpc_request("tasks/pushNotificationConfig/get", params=params)
    resp = sut_client.send_json_rpc(**req)
    
    # Should return proper JSON-RPC error for non-existent task
    assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"]), \
        "Push notifications capability declared but invalid task ID not properly rejected"
    
    # Should indicate task not found
    error_message = resp["error"]["message"].lower()
    assert "not found" in error_message or "task" in error_message, \
        "Error message should indicate task was not found"
