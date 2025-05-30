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
            ]
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
            ]
        }
    }

@quality_basic
def test_task_state_transitions(sut_client, text_message_params, follow_up_message_params):
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
    # Step 1: Create a new task with an explicit taskId
    task_id = "test-state-task-" + str(uuid.uuid4())
    create_params = text_message_params.copy()
    create_params["message"]["taskId"] = task_id
    # Add non-blocking configuration to help get intermediate states
    create_params["configuration"] = {
        "blocking": False,
        "acceptedOutputModes": ["text"]
    }
    
    create_req = message_utils.make_json_rpc_request("message/send", params=create_params)
    create_resp = sut_client.send_json_rpc(method=create_req["method"], params=create_req["params"], id=create_req["id"])
    assert message_utils.is_json_rpc_success_response(create_resp, expected_id=create_req["id"])
    
    # Verify the response (can be Task or Message)
    result = create_resp["result"]
    if "status" in result:
        # This is a Task object
        initial_state = result["status"]["state"]
        assert initial_state in {"submitted", "working"}, f"Unexpected initial state: {initial_state}"
    
    # Step 2: Get task to verify state and history
    get_req = message_utils.make_json_rpc_request("tasks/get", params={"id": task_id})
    get_resp = sut_client.send_json_rpc(method=get_req["method"], params=get_req["params"], id=get_req["id"])
    assert message_utils.is_json_rpc_success_response(get_resp, expected_id=get_req["id"])
    
    # Verify history exists and contains the initial message
    history = get_resp["result"].get("history", [])
    assert len(history) >= 1, "Task history should contain at least the initial message"
    
    # Step 3: Send a follow-up message to the task
    follow_up_params = follow_up_message_params.copy()
    follow_up_params["message"]["taskId"] = task_id
    # Add non-blocking configuration for follow-up message too
    follow_up_params["configuration"] = {
        "blocking": False,
        "acceptedOutputModes": ["text"]
    }
    update_req = message_utils.make_json_rpc_request("message/send", params=follow_up_params)
    update_resp = sut_client.send_json_rpc(method=update_req["method"], params=update_req["params"], id=update_req["id"])
    assert message_utils.is_json_rpc_success_response(update_resp, expected_id=update_req["id"])
    
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
    assert current_state in {"working", "input_required", "completed"}, f"Unexpected state: {current_state}"

@quality_basic
def test_tasks_cancel_already_canceled(sut_client):
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
    # Create a task for testing
    task_id = "test-cancel-task-" + str(uuid.uuid4())
    create_params = {
        "message": {
            "messageId": "test-cancel-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "taskId": task_id,
            "parts": [
                {"kind": "text", "text": "Task for cancel test"}
            ]
        },
        "configuration": {
            "blocking": False,
            "acceptedOutputModes": ["text"]
        }
    }
    req = message_utils.make_json_rpc_request("message/send", params=create_params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    
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