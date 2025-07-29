import pytest
import uuid

from tck import message_utils
from tck.sut_client import SUTClient
from tests.markers import mandatory_protocol


@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()

@pytest.fixture
def created_task_id(sut_client):
    # Create a task using message/send and return its id
    params = {
        "message": {
            "kind": "message",
            "messageId": "test-cancel-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {"kind": "text", "text": "Task for cancel test"}
            ]
        },
        "configuration": {
            "blocking": False,
            "acceptedOutputModes": ["text"]
        }
    }
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    # Return the server-generated task ID from the response
    return resp["result"]["id"]

@mandatory_protocol
def test_tasks_cancel_valid(sut_client, created_task_id):
    """
    MANDATORY: A2A Specification §7.4 - Task Cancellation
    
    The A2A specification requires all implementations to support
    tasks/cancel for canceling active tasks.
    
    Failure Impact: Implementation is not A2A compliant
    """
    params = {"id": created_task_id}
    req = message_utils.make_json_rpc_request("tasks/cancel", params=params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    result = resp["result"]
    assert result["id"] == created_task_id
    assert result.get("status", {}).get("state") == "canceled"

@mandatory_protocol
def test_tasks_cancel_nonexistent(sut_client):
    """
    MANDATORY: A2A Specification §7.4 - Task Not Found Error Handling
    
    The A2A specification requires proper error handling when attempting
    to cancel a non-existent task. MUST return TaskNotFoundError (-32001).
    
    Failure Impact: Implementation is not A2A compliant
    """
    params = {"id": "nonexistent-task-id"}
    req = message_utils.make_json_rpc_request("tasks/cancel", params=params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"])
    assert resp["error"]["code"] == -32001  # TaskNotFoundError
