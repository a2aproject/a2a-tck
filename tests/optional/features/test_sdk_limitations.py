"""Tests that validate A2A specification compliance for features that are commonly unimplemented.

These tests check for specification requirements that some A2A implementations
may not support correctly. They help identify compliance gaps.
"""

import time
import uuid

import pytest

from tck import message_utils
from tck.sut_client import SUTClient
from tests.markers import optional_feature


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
            "parts": [{"kind": "text", "text": "Test message for SDK limitation tests"}],
        }
    }


@optional_feature
@pytest.mark.xfail(reason="Many A2A SDK implementations do not implement historyLength parameter correctly")
def test_history_length_parameter_compliance(sut_client, text_message_params):
    """OPTIONAL FEATURE: A2A Specification Section 7.3 - historyLength Parameter Support

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

    create_req = message_utils.make_json_rpc_request("message/send", params=create_params)
    create_resp = sut_client.send_json_rpc(method=create_req["method"], params=create_req["params"], id=create_req["id"])
    assert message_utils.is_json_rpc_success_response(create_resp, expected_id=create_req["id"])

    # Get the server-generated task ID
    task_id = create_resp["result"]["id"]

    # Step 2: Add more messages to ensure we have enough history
    for i in range(5):
        follow_up_params = {
            "message": {
                "taskId": task_id,
                "messageId": f"sdk-test-msg-{i + 1}-" + str(uuid.uuid4()),
                "role": "user",
                "parts": [{"kind": "text", "text": f"SDK test message {i + 1}"}],
            }
        }
        update_req = message_utils.make_json_rpc_request("message/send", params=follow_up_params)
        update_resp = sut_client.send_json_rpc(method=update_req["method"], params=update_req["params"], id=update_req["id"])
        assert message_utils.is_json_rpc_success_response(update_resp, expected_id=update_req["id"])
        time.sleep(0.3)

    # Step 3: Get task with historyLength=2
    # Test if implementation respects the historyLength parameter
    get_limited_req = message_utils.make_json_rpc_request("tasks/get", params={"id": task_id, "historyLength": 2})
    get_limited_resp = sut_client.send_json_rpc(
        method=get_limited_req["method"], params=get_limited_req["params"], id=get_limited_req["id"]
    )
    assert message_utils.is_json_rpc_success_response(get_limited_resp, expected_id=get_limited_req["id"])

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
