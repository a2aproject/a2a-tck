import pytest
import uuid

from tck import message_utils
from tck.sut_client import SUTClient
from tests.markers import mandatory_protocol, quality_basic


@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()

@pytest.fixture
def created_task_id(sut_client):
    # Create a task using message/send and return its id
    task_id = "test-cancel-task-" + str(uuid.uuid4())
    params = {
        "message": {
            "messageId": "test-cancel-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "taskId": task_id,  # Provide the task ID explicitly
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
    # Return the task ID we provided, since the SUT may return a Message object
    return task_id

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

@quality_basic
def test_tasks_cancel_already_canceled(sut_client, created_task_id):
    """
    OPTIONAL QUALITY: A2A Specification §7.4 - Idempotent Cancellation
    
    While not explicitly required, proper error handling for attempting
    to cancel an already-canceled task indicates good implementation quality.
    
    Status: Optional quality validation for idempotency handling
    """
    params = {"id": created_task_id}
    # First cancel
    req1 = message_utils.make_json_rpc_request("tasks/cancel", params=params)
    resp1 = sut_client.send_json_rpc(method=req1["method"], params=req1["params"], id=req1["id"])
    assert message_utils.is_json_rpc_success_response(resp1, expected_id=req1["id"])
    # Second cancel (should fail)
    req2 = message_utils.make_json_rpc_request("tasks/cancel", params=params)
    resp2 = sut_client.send_json_rpc(method=req2["method"], params=req2["params"], id=req2["id"])
    assert message_utils.is_json_rpc_error_response(resp2, expected_id=req2["id"])
    # Error code for TaskNotCancelableError is implementation-specific, so just check error presence
