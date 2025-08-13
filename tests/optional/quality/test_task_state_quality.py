"""
A2A Protocol Specification: Task state management quality tests.

This test suite validates quality aspects of task state management
according to the A2A specification: https://google.github.io/A2A/specification/#task-state
"""

import time
import uuid

import pytest

from tck import message_utils
from tests.markers import quality_basic
from tests.utils import transport_helpers

# Using transport-agnostic sut_client fixture from conftest.py

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
    
    create_resp = transport_helpers.transport_send_message(sut_client, create_params)
    assert transport_helpers.is_json_rpc_success_response(create_resp)
    
    # Get the server-generated task ID
    task_id = create_resp["result"]["id"]

    # Verify the initial state and history after task creation
    get_resp = transport_helpers.transport_get_task(sut_client, task_id, history_length=1)
    assert transport_helpers.is_json_rpc_success_response(get_resp)
    
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
    
    follow_up_resp = transport_helpers.transport_send_message(sut_client, follow_up_params)
    assert transport_helpers.is_json_rpc_success_response(follow_up_resp)
    
    # Allow some time for the SUT to process the message
    time.sleep(1)
    
    # Step 4: Get task again to verify updated state and history
    get_resp2 = transport_helpers.transport_get_task(sut_client, task_id)
    assert transport_helpers.is_json_rpc_success_response(get_resp2)
    
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
    
    create_resp = transport_helpers.transport_send_message(sut_client, create_params)
    assert transport_helpers.is_json_rpc_success_response(create_resp)
    
    # Get the server-generated task ID
    task_id = create_resp["result"]["id"]
    
    params = {"id": task_id}
    # First cancel
    resp1 = transport_helpers.transport_cancel_task(sut_client, task_id)
    assert transport_helpers.is_json_rpc_success_response(resp1)
    
    # Second cancel (should fail gracefully)
    resp2 = transport_helpers.transport_cancel_task(sut_client, task_id)
    assert transport_helpers.is_json_rpc_error_response(resp2)
    # Error code for TaskNotCancelableError is implementation-specific, so just check error presence 
