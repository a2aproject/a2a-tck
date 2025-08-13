"""
Tests that validate A2A specification compliance for features that are commonly unimplemented.

These tests check for specification requirements that some A2A implementations
may not support correctly. They help identify compliance gaps.
"""

import pytest
import uuid
import time

from tck import message_utils
from tests.markers import optional_feature
from tests.utils import transport_helpers


# Using transport-agnostic sut_client fixture from conftest.py


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


@optional_feature
@pytest.mark.xfail(reason="Many A2A SDK implementations do not implement historyLength parameter correctly")
def test_history_length_parameter_compliance(sut_client, text_message_params):
    """
    OPTIONAL FEATURE: A2A Specification Section 7.3 - historyLength Parameter Support
    
    While the A2A specification requires historyLength parameter support,
    many SDK implementations struggle with this feature. This test validates
    proper implementation when present.
    
    Expected behavior per spec: When historyLength is provided in tasks/get,
    the Task.history should be limited to the most recent N messages.
    
    Test validates:
    - historyLength parameter recognition
    - Proper history truncation behavior
    - Specification compliance for this advanced feature
    """
    # Step 1: Create a task with multiple messages to build up history
    create_params = text_message_params.copy()
    
    create_resp = transport_helpers.transport_send_message(sut_client, create_params)
    assert transport_helpers.is_json_rpc_success_response(create_resp)
    
    # Get the server-generated task ID
    task_id = create_resp["result"]["id"]
    
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
        update_resp = transport_helpers.transport_send_message(sut_client, follow_up_params)
        assert transport_helpers.is_json_rpc_success_response(update_resp)
        time.sleep(0.3)
    
    # Step 3: Get task with historyLength=2 
    # Test if implementation respects the historyLength parameter 
    get_limited_resp = transport_helpers.transport_get_task(sut_client, task_id, history_length=2)
    assert transport_helpers.is_json_rpc_success_response(get_limited_resp)
    
    # Step 4: Verify specification compliance
    # The A2A specification requires this behavior
    limited_history = get_limited_resp["result"].get("history", [])
    
    # The specification requires that historyLength limits the returned history
    # A compliant implementation MUST respect this parameter
    assert len(limited_history) <= 2, (
        f"A2A specification requires historyLength=2 to limit history to 2 messages, "
        f"but got {len(limited_history)} messages. "
        f"Implementation must respect the historyLength parameter."
    ) 