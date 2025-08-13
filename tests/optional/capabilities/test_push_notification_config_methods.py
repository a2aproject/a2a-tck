import logging
import uuid

import pytest

from tck import agent_card_utils, message_utils
from tests.markers import optional_capability
from tests.capability_validator import CapabilityValidator
from tests.utils import transport_helpers

logger = logging.getLogger(__name__)

# Using transport-agnostic sut_client fixture from conftest.py

@pytest.fixture
def created_task_id(sut_client):
    # Create a task using message/send and return its id
    message_params = {
        "message": {
            "messageId": "test-push-notification-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {"kind": "text", "text": "Task for push notification config test"}
            ],
            "kind": "message"
        }
    }
    resp = transport_helpers.transport_send_message(sut_client, message_params)
    assert transport_helpers.is_json_rpc_success_response(resp)
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
    CONDITIONAL MANDATORY: A2A Specification §7.5 - Push Notification Configuration
    
    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing
            
    Test validates the tasks/pushNotificationConfig/set method for setting
    push notification configurations on tasks.
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('pushNotifications'):
        pytest.skip("Push notifications capability not declared - test not applicable")
    
    config = {
        "url": "https://example.com/webhook"
    }
    
    resp = transport_helpers.transport_set_push_notification_config(sut_client, created_task_id, config)
    
    # Since push notifications capability is declared, this MUST work
    assert transport_helpers.is_json_rpc_success_response(resp), \
        "Push notifications capability declared but set config failed"
    
    result = resp["result"]
    assert result["pushNotificationConfig"]["url"] == "https://example.com/webhook", "Push notification config URL not echoed correctly"

@optional_capability
def test_get_push_notification_config(sut_client, created_task_id, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.6 - Push Notification Configuration Retrieval
    
    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing
            
    Test validates the tasks/pushNotificationConfig/get method for retrieving
    push notification configurations from tasks.
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('pushNotifications'):
        pytest.skip("Push notifications capability not declared - test not applicable")
    
    # First, set a push notification config
    config = {
        "url": "https://example.com/webhook"
    }
    
    set_resp = transport_helpers.transport_set_push_notification_config(sut_client, created_task_id, config)
    assert transport_helpers.is_json_rpc_success_response(set_resp), \
        "Failed to set push notification config before testing get"
    
    # Now, get the config we just set
    resp = transport_helpers.transport_get_push_notification_config(sut_client, created_task_id)
    
    # Since push notifications capability is declared, this MUST work
    assert transport_helpers.is_json_rpc_success_response(resp), \
        "Push notifications capability declared but get config failed"
    
    result = resp["result"]
    assert "pushNotificationConfig" in result, "Result must contain pushNotificationConfig"
    assert "url" in result["pushNotificationConfig"], "Push notification config must have url field"
    assert result["pushNotificationConfig"]["url"] == "https://example.com/webhook", "Retrieved URL should match what was set"

@optional_capability
def test_set_push_notification_config_nonexistent(sut_client, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.5 - Push Notification Error Handling
    
    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing
            
    Test validates proper error handling for push notification config operations
    on non-existent tasks.
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('pushNotifications'):
        pytest.skip("Push notifications capability not declared - test not applicable")
    
    config = {
        "url": "https://example.com/webhook"
    }
    
    resp = transport_helpers.transport_set_push_notification_config(sut_client, "nonexistent-task-id", config)
    
    # Should return proper JSON-RPC error for non-existent task
    assert transport_helpers.is_json_rpc_error_response(resp), \
        "Push notifications capability declared but invalid task ID not properly rejected"
    
    # Should indicate task not found
    error_message = resp["error"]["message"].lower()
    assert "not found" in error_message or "task" in error_message, \
        "Error message should indicate task was not found"

@optional_capability
def test_get_push_notification_config_nonexistent(sut_client, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.6 - Push Notification Error Handling
    
    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing
            
    Test validates proper error handling for push notification config retrieval
    on non-existent tasks.
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('pushNotifications'):
        pytest.skip("Push notifications capability not declared - test not applicable")

    params = {"id": "nonexistent-task-id"}
    req = message_utils.make_json_rpc_request("tasks/pushNotificationConfig/get", params=params)
    resp = transport_helpers.transport_send_json_rpc_request(sut_client, req["method"], req.get("params"), req.get("id"))
    
    # Should return proper JSON-RPC error for non-existent task
    assert transport_helpers.is_json_rpc_error_response(resp), \
        "Push notifications capability declared but invalid task ID not properly rejected"
    
    # Should indicate task not found
    error_message = resp["error"]["message"].lower()
    assert "not found" in error_message or "task" in error_message, \
        "Error message should indicate task was not found"

@optional_capability
def test_list_push_notification_config(sut_client, created_task_id, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.7 - Push Notification Configuration List
    
    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing
            
    Test validates the tasks/pushNotificationConfig/list method for retrieving
    all push notification configurations associated with a task.
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('pushNotifications'):
        pytest.skip("Push notifications capability not declared - test not applicable")
    
    # First, set one or more push notification configs
    set_resp = transport_helpers.transport_set_push_notification_config(sut_client, created_task_id, {"url": "https://example.com/webhook1"})
    assert transport_helpers.is_json_rpc_success_response(set_resp), \
        "Failed to set push notification config before testing list"
    
    # Now, list the configs for this task
    params = {"id": created_task_id}
    req = message_utils.make_json_rpc_request("tasks/pushNotificationConfig/list", params=params)
    resp = transport_helpers.transport_send_json_rpc_request(sut_client, req["method"], req.get("params"), req.get("id"))
    
    # Since push notifications capability is declared, this MUST work
    assert transport_helpers.is_json_rpc_success_response(resp), \
        "Push notifications capability declared but list config failed"
    
    result = resp["result"]
    assert isinstance(result, list), "Result must be a list of configurations"
    assert len(result) >= 1, "Should contain at least one configuration that we just set"
    
    # Verify the configuration we set is in the list
    found_config = False
    for config in result:
        assert "pushNotificationConfig" in config, "Each config must contain pushNotificationConfig"
        assert "taskId" in config, "Each config must contain taskId"
        assert config["taskId"] == created_task_id, "TaskId should match the requested task"
        if config["pushNotificationConfig"]["url"] == "https://example.com/webhook1":
            found_config = True
    
    assert found_config, "The configuration we set should be found in the list"

@optional_capability
def test_list_push_notification_config_empty(sut_client, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.7 - Push Notification Configuration List (Empty)
    
    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing
            
    Test validates the tasks/pushNotificationConfig/list method behavior
    for tasks with no push notification configurations.
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('pushNotifications'):
        pytest.skip("Push notifications capability not declared - test not applicable")
    
    # Create a new task without any push notification configs
    params = {
        "message": {
            "messageId": "test-empty-list-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {"kind": "text", "text": "Task for empty push notification config list test"}
            ],
            "kind": "message"
        }
    }
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = transport_helpers.transport_send_json_rpc_request(sut_client, req["method"], req.get("params"), req.get("id"))
    assert transport_helpers.is_json_rpc_success_response(resp)
    empty_task_id = resp["result"]["id"]
    
    # List configs for task with no configurations
    params = {"id": empty_task_id}
    req = message_utils.make_json_rpc_request("tasks/pushNotificationConfig/list", params=params)
    resp = transport_helpers.transport_send_json_rpc_request(sut_client, req["method"], req.get("params"), req.get("id"))
    
    # Should return empty list or appropriate error - both are valid
    if transport_helpers.is_json_rpc_success_response(resp):
        result = resp["result"]
        assert isinstance(result, list), "Result must be a list"
        assert len(result) == 0, "Should be empty list for task with no configs"
    else:
        # Some implementations might return an error for no configs - this is acceptable
        assert transport_helpers.is_json_rpc_error_response(resp), \
            "Response should be either success with empty list or error"

@optional_capability
def test_delete_push_notification_config(sut_client, created_task_id, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.8 - Push Notification Configuration Delete
    
    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing
            
    Test validates the tasks/pushNotificationConfig/delete method for removing
    push notification configurations from tasks.
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('pushNotifications'):
        pytest.skip("Push notifications capability not declared - test not applicable")
    
    # First, set a push notification config
    config_params = {
        "taskId": created_task_id,
        "pushNotificationConfig": {
            "url": "https://example.com/webhook-to-delete"
        }
    }
    set_req = message_utils.make_json_rpc_request("tasks/pushNotificationConfig/set", params=config_params)
    set_resp = transport_helpers.transport_send_json_rpc_request(sut_client, set_req["method"], set_req.get("params"), set_req.get("id"))
    assert message_utils.is_json_rpc_success_response(set_resp, expected_id=set_req["id"]), \
        "Failed to set push notification config before testing delete"
    
    # Extract the config ID from the response (if provided by server)
    set_result = set_resp["result"]
    config_id = set_result["pushNotificationConfig"].get("id")
    
    if config_id:
        # If the server provides config ID, use it for deletion
        delete_params = {
            "id": created_task_id,
            "pushNotificationConfigId": config_id
        }
        req = message_utils.make_json_rpc_request("tasks/pushNotificationConfig/delete", params=delete_params)
        resp = transport_helpers.transport_send_json_rpc_request(sut_client, req["method"], req.get("params"), req.get("id"))
        
        # Since push notifications capability is declared, this MUST work
        assert transport_helpers.is_json_rpc_success_response(resp), \
            "Push notifications capability declared but delete config failed"
        
        # Result should be null for successful deletion
        result = resp["result"]
        assert result is None, "Delete should return null result on success"
        
        # Verify deletion by trying to get the config
        get_params = {"id": created_task_id}
        get_req = message_utils.make_json_rpc_request("tasks/pushNotificationConfig/get", params=get_params)
        get_resp = transport_helpers.transport_send_json_rpc_request(sut_client, get_req["method"], get_req.get("params"), get_req.get("id"))
        
        # Should either return error (config not found) or success with empty/different config
        if message_utils.is_json_rpc_success_response(get_resp, expected_id=get_req["id"]):
            # If successful, the config should be different or not contain our deleted URL
            get_result = get_resp["result"]
            if "pushNotificationConfig" in get_result:
                assert get_result["pushNotificationConfig"]["url"] != "https://example.com/webhook-to-delete", \
                    "Deleted configuration should not be retrievable"
        else:
            # Error response is also acceptable (config not found)
            assert message_utils.is_json_rpc_error_response(get_resp, expected_id=get_req["id"]), \
                "After deletion, get should either return error or different config"
    else:
        # If server doesn't provide config ID, skip this test
        pytest.skip("Server does not provide push notification config ID - cannot test delete functionality")

@optional_capability
def test_delete_push_notification_config_nonexistent(sut_client, created_task_id, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.8 - Push Notification Configuration Delete Error Handling
    
    Status: MANDATORY if capabilities.pushNotifications = true
            SKIP if capabilities.pushNotifications = false/missing
            
    Test validates proper error handling for push notification config deletion
    with non-existent task IDs or config IDs.
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('pushNotifications'):
        pytest.skip("Push notifications capability not declared - test not applicable")
    
    # Test 1: Delete with non-existent task ID
    delete_params = {
        "id": "nonexistent-task-id",
        "pushNotificationConfigId": "some-config-id"
    }
    req = message_utils.make_json_rpc_request("tasks/pushNotificationConfig/delete", params=delete_params)
    resp = transport_helpers.transport_send_json_rpc_request(sut_client, req["method"], req.get("params"), req.get("id"))
    
    # Should return proper JSON-RPC error for non-existent task
    assert transport_helpers.is_json_rpc_error_response(resp), \
        "Push notifications capability declared but invalid task ID not properly rejected"
    
    # Should indicate task not found
    error_message = resp["error"]["message"].lower()
    assert "not found" in error_message or "task" in error_message, \
        "Error message should indicate task was not found"
    
    # Test 2: Delete with valid task ID but non-existent config ID
    delete_params = {
        "id": created_task_id,
        "pushNotificationConfigId": "nonexistent-config-id"
    }
    req = message_utils.make_json_rpc_request("tasks/pushNotificationConfig/delete", params=delete_params)
    resp = transport_helpers.transport_send_json_rpc_request(sut_client, req["method"], req.get("params"), req.get("id"))
    result = resp["result"]
    assert result is None, "Delete should return null result on success"
