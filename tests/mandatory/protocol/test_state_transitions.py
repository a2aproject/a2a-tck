import time
import uuid

import pytest

from tck import message_utils
from tck.sut_client import SUTClient
from tests.markers import mandatory_protocol


@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()


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
    """MANDATORY: A2A Specification §7.3 - historyLength Parameter

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

    create_req = message_utils.make_json_rpc_request("message/send", params=create_params)
    create_resp = sut_client.send_json_rpc(**create_req)
    assert message_utils.is_json_rpc_success_response(create_resp, expected_id=create_req["id"])

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
        update_req = message_utils.make_json_rpc_request("message/send", params=follow_up_params)
        update_resp = sut_client.send_json_rpc(method=update_req["method"], params=update_req["params"], id=update_req["id"])
        assert message_utils.is_json_rpc_success_response(update_resp, expected_id=update_req["id"])
        time.sleep(0.5)  # Brief pause between messages

    # Step 3: Get task with full history
    get_full_req = message_utils.make_json_rpc_request("tasks/get", params={"id": task_id})
    get_full_resp = sut_client.send_json_rpc(method=get_full_req["method"], params=get_full_req["params"], id=get_full_req["id"])
    assert message_utils.is_json_rpc_success_response(get_full_resp, expected_id=get_full_req["id"])
    full_history = get_full_resp["result"].get("history", [])

    # Step 4: Get task with limited history (historyLength=2)
    get_limited_req = message_utils.make_json_rpc_request("tasks/get", params={"id": task_id, "historyLength": 2})
    get_limited_resp = sut_client.send_json_rpc(
        method=get_limited_req["method"], params=get_limited_req["params"], id=get_limited_req["id"]
    )
    assert message_utils.is_json_rpc_success_response(get_limited_resp, expected_id=get_limited_req["id"])
    limited_history = get_limited_resp["result"].get("history", [])

    # Verify that full history contains more entries than limited history (if available)
    if len(full_history) > 2:
        assert len(full_history) > len(limited_history), "Full history should contain more entries than limited history"

    # Verify that limited history contains at most 2 entries
    assert len(limited_history) <= 2, f"Limited history should have at most 2 entries, but has {len(limited_history)}"
