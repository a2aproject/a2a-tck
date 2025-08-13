import pytest
import uuid

from tests.markers import mandatory_protocol
from tests.utils.transport_helpers import (
    transport_send_message,
    transport_cancel_task,
    is_json_rpc_success_response,
    is_json_rpc_error_response,
    extract_task_id_from_response,
    generate_test_message_id
)


@pytest.fixture
def created_task_id(sut_client):
    # Create a task using transport-agnostic message/send and return its id
    params = {
        "message": {
            "kind": "message",
            "messageId": generate_test_message_id("cancel-test"),
            "role": "user",
            "parts": [
                {"kind": "text", "text": "Task for cancel test"}
            ]
        }
    }
    
    # Use transport-agnostic message sending
    resp = transport_send_message(sut_client, params)
    assert is_json_rpc_success_response(resp), f"Task creation failed: {resp}"
    
    # Extract task ID using transport-agnostic helper
    task_id = extract_task_id_from_response(resp)
    assert task_id is not None, "Failed to extract task ID from task creation response"
    
    return task_id

@mandatory_protocol
def test_tasks_cancel_valid(sut_client, created_task_id):
    """
    MANDATORY: A2A v0.3.0 §7.4 - Task Cancellation
    
    The A2A v0.3.0 specification requires all implementations to support
    tasks/cancel for canceling active tasks.
    This test works across all transport types (JSON-RPC, gRPC, REST).
    
    Failure Impact: Implementation is not A2A v0.3.0 compliant
    
    Specification Reference: A2A v0.3.0 §7.4 - Task Cancellation
    """
    # Use transport-agnostic task cancellation
    resp = transport_cancel_task(sut_client, created_task_id)
    assert is_json_rpc_success_response(resp), f"Task cancellation failed: {resp}"
    
    # Extract result from transport response
    result = resp.get("result", resp)
    
    # Validate cancellation response according to A2A v0.3.0 specification
    assert result["id"] == created_task_id, f"Task ID mismatch: expected {created_task_id}, got {result.get('id')}"
    
    # Check that task status indicates cancellation
    status = result.get("status", {})
    if isinstance(status, dict):
        assert status.get("state") == "canceled", f"Expected canceled state, got: {status.get('state')}"
    else:
        # Handle case where status might be a string
        assert status == "canceled", f"Expected canceled status, got: {status}"

@mandatory_protocol
def test_tasks_cancel_nonexistent(sut_client):
    """
    MANDATORY: A2A v0.3.0 §7.4 - Task Not Found Error Handling
    
    The A2A v0.3.0 specification requires proper error handling when attempting
    to cancel a non-existent task. MUST return TaskNotFoundError (-32001).
    This test works across all transport types (JSON-RPC, gRPC, REST).
    
    Failure Impact: Implementation is not A2A v0.3.0 compliant
    
    Specification Reference: A2A v0.3.0 §7.4 - Task Cancellation
    """
    # Use transport-agnostic task cancellation for non-existent task
    resp = transport_cancel_task(sut_client, "nonexistent-task-id")
    
    # Should receive an error response
    assert not is_json_rpc_success_response(resp), f"Expected error for non-existent task, got: {resp}"
    assert "error" in resp, f"Response should contain error field: {resp}"
    
    # Validate A2A v0.3.0 TaskNotFoundError code
    error_code = resp["error"].get("code")
    assert error_code == -32001, f"Expected TaskNotFoundError (-32001), got error code: {error_code}"
