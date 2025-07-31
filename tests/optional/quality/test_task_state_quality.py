"""
A2A Protocol Specification: Task state management quality tests.

This test suite validates quality aspects of task state management
according to the A2A specification: https://google.github.io/A2A/specification/#task-state
"""

import time
import uuid

import pytest

from tck import message_utils
from tck.sut_client import SUTClient
from tests.markers import quality_basic

@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()

@pytest.fixture
def text_message_params():
    """Create a basic text message params object"""
    return {
        "message": {
            "messageId": "test-state-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Hello from TCK state transition test!"
                }
            ],
            "kind": "message"
        }
    }

@pytest.fixture
def follow_up_message_params(text_message_params):
    """Create a follow-up message params object"""
    return {
        "message": {
            "messageId": "test-followup-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Follow-up message for state transition test"
                }
            ],
            "kind": "message"
        }
    }

@quality_basic
def test_task_state_transitions(sut_client):
    """
    QUALITY BASIC: A2A Specification §6.3 - Task State Management
    
    While not explicitly mandated, proper task state transitions indicate
    good implementation quality and adherence to the state model.
    
    Tests implementation quality for state management and transitions.
    
    Failure Impact: Affects user experience quality (perfectly acceptable)
    Fix Suggestion: Implement proper task state transitions and history management
    
    Asserts:
        - Task states transition logically through valid states
        - Task history is maintained and updated correctly
        - Follow-up messages update task state appropriately
    """
    # Create a task
    create_params = {
        "message": {
            "kind": "message",
            "messageId": "test-state-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {"kind": "text", "text": "Task for state transition test"}
            ]
        }
    }
    
    create_req = message_utils.make_json_rpc_request("message/send", params=create_params)
    create_resp = sut_client.send_json_rpc(**create_req)
    assert message_utils.is_json_rpc_success_response(create_resp, expected_id=create_req["id"])
    
    # Get the server-generated task ID
    task_id = create_resp["result"]["id"]

    # Verify the initial state and history after task creation
    get_req = message_utils.make_json_rpc_request("tasks/get", params={"id": task_id, "historyLength": 1})
    get_resp = sut_client.send_json_rpc(**get_req)
    assert message_utils.is_json_rpc_success_response(get_resp, expected_id=get_req["id"])
    
    task_after_creation = get_resp["result"]
    initial_state = task_after_creation.get("status", {}).get("state")
    assert initial_state in {"submitted", "working"}, f"Unexpected initial state: {initial_state}"

    # Verify history exists and contains the initial message
    history = task_after_creation.get("history", [])
    assert len(history) == 1, "Task history should contain the initial message when requested"
    # Send a follow-up message to continue the task
    follow_up_params = {
        "message": {
            "kind": "message",
            "messageId": "test-followup-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "taskId": task_id,
            "parts": [
                {"kind": "text", "text": "Follow-up for state test"}
            ]
        }
    }
    
    follow_up_req = message_utils.make_json_rpc_request("message/send", params=follow_up_params)
    follow_up_resp = sut_client.send_json_rpc(**follow_up_req)
    assert message_utils.is_json_rpc_success_response(follow_up_resp, expected_id=follow_up_req["id"])
    
    # Allow some time for the SUT to process the message
    time.sleep(1)
    
    # Step 4: Get task again to verify updated state and history
    get_req2 = message_utils.make_json_rpc_request("tasks/get", params={"id": task_id})
    get_resp2 = sut_client.send_json_rpc(method=get_req2["method"], params=get_req2["params"], id=get_req2["id"])
    assert message_utils.is_json_rpc_success_response(get_resp2, expected_id=get_req2["id"])
    
    # Verify updated history contains the follow-up message
    updated_history = get_resp2["result"].get("history", [])
    assert len(updated_history) >= 2, "Task history should contain the initial and follow-up messages"
    
    # Verify the state transitions - simple check that it's in an expected state
    current_state = get_resp2["result"]["status"]["state"]
    assert current_state in {"working", "input-required", "completed"}, f"Unexpected state: {current_state}"

@quality_basic
def test_task_cancel_state_handling(sut_client):
    """
    QUALITY BASIC: A2A Specification §7.4 - Idempotent Cancellation
    
    While not explicitly required, proper error handling for attempting
    to cancel an already-canceled task indicates good implementation quality.
    
    Tests implementation quality for idempotency handling in cancellation.
    
    Failure Impact: Affects user experience quality (perfectly acceptable)
    Fix Suggestion: Implement proper idempotency handling for cancellation operations
    
    Asserts:
        - First cancellation succeeds for active task
        - Second cancellation returns appropriate error
        - Error handling is consistent and predictable
    """
    # Create a task
    create_params = {
        "message": {
            "kind": "message",
            "messageId": "test-cancel-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {"kind": "text", "text": "Task for cancel test"}
            ]
        }
    }
    
    create_req = message_utils.make_json_rpc_request("message/send", params=create_params)
    create_resp = sut_client.send_json_rpc(**create_req)
    assert message_utils.is_json_rpc_success_response(create_resp, expected_id=create_req["id"])
    
    # Get the server-generated task ID
    task_id = create_resp["result"]["id"]
    
    params = {"id": task_id}
    # First cancel
    req1 = message_utils.make_json_rpc_request("tasks/cancel", params=params)
    resp1 = sut_client.send_json_rpc(method=req1["method"], params=req1["params"], id=req1["id"])
    assert message_utils.is_json_rpc_success_response(resp1, expected_id=req1["id"])
    
    # Second cancel (should fail gracefully)
    req2 = message_utils.make_json_rpc_request("tasks/cancel", params=params)
    resp2 = sut_client.send_json_rpc(method=req2["method"], params=req2["params"], id=req2["id"])
    assert message_utils.is_json_rpc_error_response(resp2, expected_id=req2["id"])
    # Error code for TaskNotCancelableError is implementation-specific, so just check error presence 
