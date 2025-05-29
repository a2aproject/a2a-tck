import pytest
import uuid

from tck import message_utils
from tck.sut_client import SUTClient


@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()

@pytest.fixture
def created_task_id(sut_client):
    # Create a task using message/send and return its id
    task_id = "test-get-task-" + str(uuid.uuid4())
    params = {
        "message": {
            "messageId": "test-get-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "taskId": task_id,  # Provide the task ID explicitly
            "parts": [
                {"kind": "text", "text": "Task for get test"}
            ]
        }
    }
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    # Return the task ID we provided, since the SUT may return a Message object
    return task_id

@pytest.mark.core
def test_tasks_get_valid(sut_client, created_task_id):
    """
    A2A JSON-RPC Spec: tasks/get
    Test retrieving a task's state and history by id. Expect a Task object in result.
    """
    params = {"id": created_task_id}
    req = message_utils.make_json_rpc_request("tasks/get", params=params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    result = resp["result"]
    assert result["id"] == created_task_id
    assert "status" in result

@pytest.mark.core
def test_tasks_get_with_history_length(sut_client, created_task_id):
    """
    MANDATORY: A2A Specification Section 7.3 - historyLength parameter
    
    The A2A specification states that tasks/get MUST support the historyLength parameter
    to limit the number of history entries returned.
    
    Test retrieving a task with historyLength param. Expect a Task object in result.
    """
    params = {"id": created_task_id, "historyLength": 1}
    req = message_utils.make_json_rpc_request("tasks/get", params=params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    result = resp["result"]
    assert result["id"] == created_task_id
    assert "history" in result

@pytest.mark.core
def test_tasks_get_nonexistent(sut_client):
    """
    A2A JSON-RPC Spec: tasks/get
    Test retrieving a non-existent task. Expect TaskNotFoundError.
    """
    params = {"id": "nonexistent-task-id"}
    req = message_utils.make_json_rpc_request("tasks/get", params=params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"])
    assert resp["error"]["code"] == -32001  # TaskNotFoundError
