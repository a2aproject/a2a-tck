import time
import uuid

import pytest

from tck import message_utils
from tck.sut_client import SUTClient
from tests.markers import mandatory_protocol


# Using transport-agnostic sut_client fixture from conftest.py


@pytest.fixture
def text_message_params():
    """Create a basic text message params object"""
    return {
        "message": {
            "kind": "message",
            "messageId": "test-state-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [{"kind": "text", "text": "Hello from TCK state transition test!"}],
        }
    }


@pytest.fixture
def follow_up_message_params(text_message_params):
    """Create a follow-up message params object"""
    return {
        "message": {
            "kind": "message",
            "messageId": "test-followup-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [{"kind": "text", "text": "Follow-up message for state transition test"}],
        }
    }


@mandatory_protocol
def test_task_history_length(sut_client):
    """
    MANDATORY: A2A Specification §7.3 - historyLength Parameter

    The A2A specification states that tasks/get MUST support the historyLength
    parameter to limit the number of history entries returned.

    Failure Impact: Implementation is not A2A compliant
    """
    # Create a task and add multiple messages to build history
    create_params = {
        "message": {
            "kind": "message",
            "messageId": "test-history-create-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [{"kind": "text", "text": "Initial message for history test"}],
        }
    }

    from tests.utils import transport_helpers

    create_resp = transport_helpers.transport_send_message(sut_client, create_params)
    assert transport_helpers.is_json_rpc_success_response(create_resp)

    # Get the server-generated task ID
    task_id = create_resp["result"]["id"]

    # Add additional messages to the task to build history
    for i in range(3):
        follow_up_params = {
            "message": {
                "kind": "message",
                "messageId": f"test-history-message-{i + 1}-" + str(uuid.uuid4()),
                "role": "user",
                "taskId": task_id,
                "parts": [{"kind": "text", "text": f"Follow-up message {i + 1} for history test"}],
            }
        }
        update_resp = transport_helpers.transport_send_message(sut_client, follow_up_params)
        assert transport_helpers.is_json_rpc_success_response(update_resp)
        time.sleep(0.5)  # Brief pause between messages

    # Step 3: Get task with full history
    get_full_resp = transport_helpers.transport_get_task(sut_client, task_id)
    assert transport_helpers.is_json_rpc_success_response(get_full_resp)
    full_history = get_full_resp["result"].get("history", [])

    # Step 4: Get task with limited history (historyLength=2)
    get_limited_resp = transport_helpers.transport_get_task(sut_client, task_id, history_length=2)
    assert transport_helpers.is_json_rpc_success_response(get_limited_resp)
    limited_history = get_limited_resp["result"].get("history", [])

    # Verify that full history contains more entries than limited history (if available)
    if len(full_history) > 2:
        assert len(full_history) > len(limited_history), "Full history should contain more entries than limited history"

    # Verify that limited history contains at most 2 entries
    assert len(limited_history) <= 2, f"Limited history should have at most 2 entries, but has {len(limited_history)}"
