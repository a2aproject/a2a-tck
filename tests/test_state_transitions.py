import time

import pytest

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
            "parts": [
                {
                    "kind": "text",
                    "text": "Hello from TCK state transition test!"
                }
            ]
        }
    }

@pytest.fixture
def follow_up_message_params(text_message_params):
    """Create a follow-up message params object"""
    return {
        "message": {
            "parts": [
                {
                    "kind": "text",
                    "text": "Follow-up message for state transition test"
                }
            ]
        }
    }

@pytest.mark.core
def test_task_state_transitions(sut_client, text_message_params, follow_up_message_params):
    """
    A2A JSON-RPC Spec: Task State Transitions
    Test that a task transitions through expected states and maintains its history correctly.
    
    This tests sends multiple messages to a task and verifies its state transitions using tasks/get.
    """
    # Step 1: Create a new task
    create_req = message_utils.make_json_rpc_request("message/send", params=text_message_params)
    create_resp = sut_client.send_json_rpc(method=create_req["method"], params=create_req["params"], id=create_req["id"])
    assert message_utils.is_json_rpc_success_response(create_resp, expected_id=create_req["id"])
    task_id = create_resp["result"]["id"]
    
    # Verify initial state (typically "submitted" or "working")
    initial_state = create_resp["result"]["status"]["state"]
    assert initial_state in {"submitted", "working"}, f"Unexpected initial state: {initial_state}"
    
    # Step 2: Get task to verify state and history
    get_req = message_utils.make_json_rpc_request("tasks/get", params={"taskId": task_id})
    get_resp = sut_client.send_json_rpc(method=get_req["method"], params=get_req["params"], id=get_req["id"])
    assert message_utils.is_json_rpc_success_response(get_resp, expected_id=get_req["id"])
    
    # Verify history exists and contains the initial message
    history = get_resp["result"].get("history", [])
    assert len(history) >= 1, "Task history should contain at least the initial message"
    
    # Step 3: Send a follow-up message to the task
    follow_up_params = follow_up_message_params.copy()
    follow_up_params["message"]["taskId"] = task_id
    update_req = message_utils.make_json_rpc_request("message/send", params=follow_up_params)
    update_resp = sut_client.send_json_rpc(method=update_req["method"], params=update_req["params"], id=update_req["id"])
    assert message_utils.is_json_rpc_success_response(update_resp, expected_id=update_req["id"])
    
    # Allow some time for the SUT to process the message
    time.sleep(1)
    
    # Step 4: Get task again to verify updated state and history
    get_req2 = message_utils.make_json_rpc_request("tasks/get", params={"taskId": task_id})
    get_resp2 = sut_client.send_json_rpc(**get_req2)
    assert message_utils.is_json_rpc_success_response(get_resp2, expected_id=get_req2["id"])
    
    # Verify updated history contains the follow-up message
    updated_history = get_resp2["result"].get("history", [])
    assert len(updated_history) >= 2, "Task history should contain the initial and follow-up messages"
    
    # Verify the state transitions - simple check that it's in an expected state
    current_state = get_resp2["result"]["status"]["state"]
    assert current_state in {"working", "input_required", "completed"}, f"Unexpected state: {current_state}"

@pytest.mark.core
def test_task_history_length(sut_client, text_message_params):
    """
    A2A JSON-RPC Spec: Task History Length Parameter
    Test that the historyLength parameter in tasks/get properly limits the history entries returned.
    """
    # Step 1: Create a new task
    create_req = message_utils.make_json_rpc_request("message/send", params=text_message_params)
    create_resp = sut_client.send_json_rpc(method=create_req["method"], params=create_req["params"], id=create_req["id"])
    assert message_utils.is_json_rpc_success_response(create_resp, expected_id=create_req["id"])
    task_id = create_resp["result"]["id"]
    
    # Step 2: Send additional messages to build up history
    for i in range(3):
        follow_up_params = {
            "message": {
                "taskId": task_id,
                "parts": [
                    {
                        "kind": "text",
                        "text": f"Follow-up message {i+1}"
                    }
                ]
            }
        }
        update_req = message_utils.make_json_rpc_request("message/send", params=follow_up_params)
        update_resp = sut_client.send_json_rpc(method=update_req["method"], params=update_req["params"], id=update_req["id"])
        assert message_utils.is_json_rpc_success_response(update_resp, expected_id=update_req["id"])
        time.sleep(0.5)  # Brief pause between messages
    
    # Step 3: Get task with full history
    get_full_req = message_utils.make_json_rpc_request("tasks/get", params={"taskId": task_id})
    get_full_resp = sut_client.send_json_rpc(method=get_full_req["method"], params=get_full_req["params"], id=get_full_req["id"])
    assert message_utils.is_json_rpc_success_response(get_full_resp, expected_id=get_full_req["id"])
    full_history = get_full_resp["result"].get("history", [])
    
    # Step 4: Get task with limited history (historyLength=2)
    get_limited_req = message_utils.make_json_rpc_request("tasks/get", params={"taskId": task_id, "historyLength": 2})
    get_limited_resp = sut_client.send_json_rpc(**get_limited_req)
    assert message_utils.is_json_rpc_success_response(get_limited_resp, expected_id=get_limited_req["id"])
    limited_history = get_limited_resp["result"].get("history", [])
    
    # Verify that limited history contains at most 2 entries
    assert len(limited_history) <= 2, f"Limited history should have at most 2 entries, but has {len(limited_history)}"
    
    # Verify that full history contains more entries than limited history (if available)
    if len(full_history) > 2:
        assert len(full_history) > len(limited_history), "Full history should contain more entries than limited history" 