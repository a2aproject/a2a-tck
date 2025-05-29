"""
Tests that document known limitations in the A2A SDK.

These tests verify that the SDK doesn't implement certain A2A specification 
features correctly, and that our SUT workarounds are needed.
"""

import pytest
import uuid
import time

from tck import message_utils
from tck.sut_client import SUTClient


@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()


@pytest.fixture
def text_message_params():
    """Create a basic text message params object"""
    return {
        "message": {
            "messageId": "test-sdk-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Test message for SDK limitation tests"
                }
            ]
        }
    }


@pytest.mark.xfail(reason="Documenting SDK DefaultRequestHandler limitation: historyLength parameter not implemented")
def test_sdk_default_handler_history_length_bug(sut_client, text_message_params):
    """
    A2A Specification Section 7.3: tasks/get historyLength parameter
    
    This test documents that the SDK's DefaultRequestHandler does not implement
    the historyLength parameter as required by the A2A specification.
    
    Expected behavior per spec: When historyLength is provided in tasks/get,
    the Task.history should be limited to the most recent N messages.
    
    SDK Reality: DefaultRequestHandler ignores historyLength parameter completely.
    
    Our SUT works because it uses TckCoreRequestHandler (custom implementation).
    If this test passes, it means either:
    1. The SDK bug has been fixed, OR
    2. Our SUT is using the DefaultRequestHandler instead of TckCoreRequestHandler
    
    Note: This test is marked as xfail to document the SDK limitation.
    If the SDK is ever fixed, this test will start passing and should be reviewed.
    """
    # Step 1: Create a task with multiple messages to build up history
    task_id = "test-sdk-limitation-" + str(uuid.uuid4())
    create_params = text_message_params.copy()
    create_params["message"]["taskId"] = task_id
    
    create_req = message_utils.make_json_rpc_request("message/send", params=create_params)
    create_resp = sut_client.send_json_rpc(method=create_req["method"], params=create_req["params"], id=create_req["id"])
    assert message_utils.is_json_rpc_success_response(create_resp, expected_id=create_req["id"])
    
    # Step 2: Add more messages to ensure we have enough history
    for i in range(5):
        follow_up_params = {
            "message": {
                "taskId": task_id,
                "messageId": f"sdk-test-msg-{i+1}-" + str(uuid.uuid4()),
                "role": "user",
                "parts": [
                    {
                        "kind": "text", 
                        "text": f"SDK test message {i+1}"
                    }
                ]
            }
        }
        update_req = message_utils.make_json_rpc_request("message/send", params=follow_up_params)
        update_resp = sut_client.send_json_rpc(method=update_req["method"], params=update_req["params"], id=update_req["id"])
        assert message_utils.is_json_rpc_success_response(update_resp, expected_id=update_req["id"])
        time.sleep(0.3)
    
    # Step 3: Get task with historyLength=2 
    # If SDK DefaultRequestHandler were used, this would be ignored
    get_limited_req = message_utils.make_json_rpc_request("tasks/get", params={"id": task_id, "historyLength": 2})
    get_limited_resp = sut_client.send_json_rpc(method=get_limited_req["method"], params=get_limited_req["params"], id=get_limited_req["id"])
    assert message_utils.is_json_rpc_success_response(get_limited_resp, expected_id=get_limited_req["id"])
    
    # Step 4: Verify the specification behavior
    # This is what SHOULD happen according to A2A spec
    limited_history = get_limited_resp["result"].get("history", [])
    
    # The specification requires that historyLength limits the returned history
    # SDK DefaultRequestHandler ignores this parameter, so this assertion would fail
    assert len(limited_history) <= 2, (
        f"A2A spec requires historyLength=2 to limit history to 2 messages, "
        f"but got {len(limited_history)} messages. "
        f"This suggests SDK DefaultRequestHandler is being used (bug) instead of custom handler."
    )
    
    # If we reach here, it means our SUT workaround is working correctly
    # This test will be marked as xfail to document the SDK limitation


@pytest.mark.core
def test_sut_workaround_implements_history_length_correctly(sut_client, text_message_params):
    """
    Verify that our SUT correctly implements historyLength parameter.
    
    This test documents that our TckCoreRequestHandler workaround correctly
    implements the A2A specification requirement for historyLength.
    
    This test should always PASS because our SUT uses the custom handler.
    """
    # Create task with history
    task_id = "test-workaround-correct-" + str(uuid.uuid4())
    create_params = text_message_params.copy()
    create_params["message"]["taskId"] = task_id
    
    create_req = message_utils.make_json_rpc_request("message/send", params=create_params)
    create_resp = sut_client.send_json_rpc(method=create_req["method"], params=create_req["params"], id=create_req["id"])
    assert message_utils.is_json_rpc_success_response(create_resp, expected_id=create_req["id"])
    
    # Add multiple messages
    for i in range(4):
        follow_up_params = {
            "message": {
                "taskId": task_id,
                "messageId": f"workaround-msg-{i+1}-" + str(uuid.uuid4()),
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": f"Workaround test message {i+1}"
                    }
                ]
            }
        }
        update_req = message_utils.make_json_rpc_request("message/send", params=follow_up_params)
        update_resp = sut_client.send_json_rpc(method=update_req["method"], params=update_req["params"], id=update_req["id"])
        assert message_utils.is_json_rpc_success_response(update_resp, expected_id=update_req["id"])
        time.sleep(0.2)
    
    # Test different historyLength values
    for history_length in [1, 2, 3]:
        get_req = message_utils.make_json_rpc_request("tasks/get", params={"id": task_id, "historyLength": history_length})
        get_resp = sut_client.send_json_rpc(method=get_req["method"], params=get_req["params"], id=get_req["id"])
        assert message_utils.is_json_rpc_success_response(get_resp, expected_id=get_req["id"])
        
        history = get_resp["result"].get("history", [])
        assert len(history) <= history_length, (
            f"historyLength={history_length} should limit history to {history_length} messages, "
            f"but got {len(history)} messages"
        )
        
        # Verify we actually have some history (task isn't empty)
        if history_length > 0:
            assert len(history) > 0, "Task should have some history messages" 