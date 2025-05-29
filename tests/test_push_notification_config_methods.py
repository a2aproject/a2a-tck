import logging
import uuid

import pytest

from tck import agent_card_utils, message_utils
from tck.sut_client import SUTClient

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
            ]
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

def test_set_push_notification_config(sut_client, created_task_id, agent_card_data):
    """
    A2A JSON-RPC Spec: tasks/pushNotificationConfig/set
    Test setting push notification config for a valid task. 
    Expect echoed config in result or UnsupportedOperationError if not supported.
    
    A2A Specification Compliance: If the agent supports push notification functionality,
    it MUST declare pushNotifications capability in the Agent Card. This test will FAIL
    (not skip) if the capability is missing but the agent actually supports push notifications.
    """
    # Check if push notifications are supported
    push_supported = has_push_notification_support(agent_card_data)
    
    # A2A Specification Compliance Check
    if agent_card_data is not None and not push_supported:
        pytest.fail(
            "Agent doesn't declare pushNotifications capability in Agent Card. "
            "A2A specification requires agents to declare all supported capabilities. "
            "If the agent supports push notifications, add 'capabilities.pushNotifications: true' to Agent Card. "
            "If the agent doesn't support push notifications, this test should return PushNotificationNotSupportedError."
        )
    
    # Apply appropriate marker based on capability
    if push_supported:
        pytestmark = pytest.mark.core
    else:
        pytestmark = pytest.mark.all
    
    config_params = {
        "taskId": created_task_id,
        "config": {
            "type": "webhook",
            "url": "https://example.com/webhook"
        }
    }
    req = message_utils.make_json_rpc_request("tasks/pushNotificationConfig/set", params=config_params)
    resp = sut_client.send_json_rpc(**req)
    
    if message_utils.is_json_rpc_success_response(resp, expected_id=req["id"]):
        # If we get a success response, push notifications are supported
        # (regardless of what Agent Card says)
        result = resp["result"]
        assert result["type"] == "webhook"
        assert result["url"] == "https://example.com/webhook"
        
        # Log a warning if Agent Card contradicts this
        if agent_card_data is not None and not push_supported:
            logger.warning("Agent Card claims push notifications aren't supported, but SUT accepted the request")
    else:
        # If not supported, expect UnsupportedOperationError or MethodNotFound
        assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"])
        assert resp["error"]["code"] in (-32002, -32601)  # -32002: unsupported, -32601: method not found
        
        # Log a warning if Agent Card contradicts this
        if push_supported:
            logger.warning("Agent Card claims push notifications are supported, but SUT rejected the request")

def test_get_push_notification_config(sut_client, created_task_id, agent_card_data):
    """
    A2A JSON-RPC Spec: tasks/pushNotificationConfig/get
    Test getting push notification config for a valid task. 
    Expect config in result or UnsupportedOperationError if not supported.
    
    A2A Specification Compliance: If the agent supports push notification functionality,
    it MUST declare pushNotifications capability in the Agent Card.
    """
    # Check if push notifications are supported
    push_supported = has_push_notification_support(agent_card_data)
    
    # A2A Specification Compliance Check
    if agent_card_data is not None and not push_supported:
        pytest.fail(
            "Agent doesn't declare pushNotifications capability in Agent Card. "
            "A2A specification requires agents to declare all supported capabilities. "
            "If the agent supports push notifications, add 'capabilities.pushNotifications: true' to Agent Card. "
            "If the agent doesn't support push notifications, this test should return PushNotificationNotSupportedError."
        )
    
    # Apply appropriate marker based on capability
    if push_supported:
        pytestmark = pytest.mark.core
    else:
        pytestmark = pytest.mark.all
    
    params = {"taskId": created_task_id}
    req = message_utils.make_json_rpc_request("tasks/pushNotificationConfig/get", params=params)
    resp = sut_client.send_json_rpc(**req)
    
    if message_utils.is_json_rpc_success_response(resp, expected_id=req["id"]):
        # If we get a success response, push notifications are supported
        result = resp["result"]
        assert "type" in result
        
        # Log a warning if Agent Card contradicts this
        if agent_card_data is not None and not push_supported:
            logger.warning("Agent Card claims push notifications aren't supported, but SUT accepted the request")
    else:
        # If not supported, expect UnsupportedOperationError or MethodNotFound
        assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"])
        assert resp["error"]["code"] in (-32002, -32601)
        
        # Log a warning if Agent Card contradicts this
        if push_supported:
            logger.warning("Agent Card claims push notifications are supported, but SUT rejected the request")

def test_set_push_notification_config_nonexistent(sut_client, agent_card_data):
    """
    A2A JSON-RPC Spec: tasks/pushNotificationConfig/set
    Test setting push notification config for a non-existent task. 
    Expect TaskNotFoundError or UnsupportedOperationError.
    
    A2A Specification Compliance: If the agent supports push notification functionality,
    it MUST declare pushNotifications capability in the Agent Card.
    """
    # Check if push notifications are supported
    push_supported = has_push_notification_support(agent_card_data)
    
    # A2A Specification Compliance Check
    if agent_card_data is not None and not push_supported:
        pytest.fail(
            "Agent doesn't declare pushNotifications capability in Agent Card. "
            "A2A specification requires agents to declare all supported capabilities. "
            "If the agent supports push notifications, add 'capabilities.pushNotifications: true' to Agent Card. "
            "If the agent doesn't support push notifications, this test should return PushNotificationNotSupportedError."
        )
    
    # Apply appropriate marker based on capability
    if push_supported:
        pytestmark = pytest.mark.core
    else:
        pytestmark = pytest.mark.all
    
    config_params = {
        "taskId": "nonexistent-task-id",
        "config": {
            "type": "webhook",
            "url": "https://example.com/webhook"
        }
    }
    req = message_utils.make_json_rpc_request("tasks/pushNotificationConfig/set", params=config_params)
    resp = sut_client.send_json_rpc(**req)
    
    # Should be an error response regardless
    assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"])
    
    # Error code could be TaskNotFound, Unsupported, or MethodNotFound
    assert resp["error"]["code"] in (-32001, -32002, -32601)
    
    # If push notifications are supported, it should be a TaskNotFoundError
    if push_supported:
        # Ideally we'd check for a specific error code for TaskNotFoundError,
        # but different SUTs might use different codes
        error_message = resp["error"]["message"].lower()
        if "not found" not in error_message and "task" not in error_message:
            logger.warning("Expected TaskNotFoundError but got a different error message")

def test_get_push_notification_config_nonexistent(sut_client, agent_card_data):
    """
    A2A JSON-RPC Spec: tasks/pushNotificationConfig/get
    Test getting push notification config for a non-existent task. 
    Expect TaskNotFoundError or UnsupportedOperationError.
    
    A2A Specification Compliance: If the agent supports push notification functionality,
    it MUST declare pushNotifications capability in the Agent Card.
    """
    # Check if push notifications are supported
    push_supported = has_push_notification_support(agent_card_data)
    
    # A2A Specification Compliance Check
    if agent_card_data is not None and not push_supported:
        pytest.fail(
            "Agent doesn't declare pushNotifications capability in Agent Card. "
            "A2A specification requires agents to declare all supported capabilities. "
            "If the agent supports push notifications, add 'capabilities.pushNotifications: true' to Agent Card. "
            "If the agent doesn't support push notifications, this test should return PushNotificationNotSupportedError."
        )
    
    # Apply appropriate marker based on capability
    if push_supported:
        pytestmark = pytest.mark.core
    else:
        pytestmark = pytest.mark.all
    
    params = {"taskId": "nonexistent-task-id"}
    req = message_utils.make_json_rpc_request("tasks/pushNotificationConfig/get", params=params)
    resp = sut_client.send_json_rpc(**req)
    
    # Should be an error response regardless
    assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"])
    
    # Error code could be TaskNotFound, Unsupported, or MethodNotFound
    assert resp["error"]["code"] in (-32001, -32002, -32601)
    
    # If push notifications are supported, it should be a TaskNotFoundError
    if push_supported:
        error_message = resp["error"]["message"].lower()
        if "not found" not in error_message and "task" not in error_message:
            logger.warning("Expected TaskNotFoundError but got a different error message")
