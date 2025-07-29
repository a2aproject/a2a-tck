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
            "messageId": "test-get-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {"kind": "text", "text": "Task for get test"}
            ]
        }
    }
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    # Return the server-generated task ID from the response
    return resp["result"]["id"]

@mandatory_protocol
def test_tasks_get_valid(sut_client, created_task_id):
    """
    MANDATORY: A2A Specification §7.3 - Task Retrieval
    
    The A2A specification requires all implementations to support
    tasks/get for retrieving task state and history by ID.
    
    Failure Impact: Implementation is not A2A compliant
    """
    params = {"id": created_task_id}
    req = message_utils.make_json_rpc_request("tasks/get", params=params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    result = resp["result"]
    assert result["id"] == created_task_id
    assert "status" in result

@mandatory_protocol
def test_tasks_get_with_history_length(sut_client, created_task_id):
    """
    MANDATORY: A2A Specification §7.3 - historyLength Parameter
    
    The A2A specification states that tasks/get MUST support the historyLength 
    parameter to limit the number of history entries returned.
    
    Failure Impact: Implementation is not A2A compliant
    """
    params = {"id": created_task_id, "historyLength": 1}
    req = message_utils.make_json_rpc_request("tasks/get", params=params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    result = resp["result"]
    assert result["id"] == created_task_id
    assert "history" in result

@mandatory_protocol
def test_tasks_get_nonexistent(sut_client):
    """
    MANDATORY: A2A Specification §7.3 - Task Not Found Error Handling
    
    The A2A specification requires proper error handling when attempting
    to retrieve a non-existent task. MUST return TaskNotFoundError (-32001).
    
    Failure Impact: Implementation is not A2A compliant
    """
    params = {"id": "nonexistent-task-id"}
    req = message_utils.make_json_rpc_request("tasks/get", params=params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"])
    assert resp["error"]["code"] == -32001  # TaskNotFoundError
