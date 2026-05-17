import pytest

from tests.markers import mandatory_protocol
from tests.utils.transport_helpers import (
    transport_send_message,
    transport_cancel_task,
    is_json_rpc_success_response,
    extract_task_id_from_response,
    generate_test_message_id,
)


@pytest.fixture
def created_task_id(sut_client):
    # Create a task using transport-agnostic SendMessage and return its id
    params = {
        "message": {
            "messageId": generate_test_message_id("cancel-test"),
            "role": "ROLE_USER",
            "parts": [{"text": "Task for cancel test"}],
        }
    }

    # Use transport-agnostic message sending
    resp = transport_send_message(sut_client, params)
    assert is_json_rpc_success_response(resp), f"Task creation failed: {resp}"
    print(f"resp = {resp}")

    # Extract task ID using transport-agnostic helper
    task_id = extract_task_id_from_response(resp)
    assert task_id is not None, "Failed to extract task ID from task creation response"

    return task_id


def assert_cancel_response_valid(resp, task_id):
    """Validate a task cancellation response while tolerating completed-task races."""
    if not is_json_rpc_success_response(resp):
        error = resp.get("error", {})
        error_code = error.get("code") if isinstance(error, dict) else None
        assert error_code == -32002, (
            "Task cancellation failed with an unexpected error: "
            f"expected TaskNotCancelableError (-32002) for already-completed tasks, got: {resp}"
        )
        return

    # Extract result from transport response
    result = resp.get("result", resp)

    # Validate cancellation response according to A2A v1.0 specification
    assert result["id"] == task_id, f"Task ID mismatch: expected {task_id}, got {result.get('id')}"

    # Check that task status indicates cancellation
    status = result.get("status", {})
    if isinstance(status, dict):
        assert (
            status.get("state") == "TASK_STATE_CANCELED"
        ), f"Expected canceled state, got: {status.get('state')}"
    else:
        # Handle case where status might be a string
        assert status == "TASK_STATE_CANCELED", f"Expected canceled status, got: {status}"


def test_cancel_response_accepts_not_cancelable_completed_task():
    """Completed tasks may legitimately reject cancellation as not cancelable."""
    assert_cancel_response_valid(
        {
            "jsonrpc": "2.0",
            "id": "test-request",
            "error": {
                "code": -32002,
                "message": "Task cannot be canceled - current state: 3",
            },
        },
        "completed-task-id",
    )


def test_cancel_response_rejects_unexpected_errors():
    """Unexpected cancel errors should still fail the compliance test."""
    with pytest.raises(AssertionError, match="unexpected error"):
        assert_cancel_response_valid(
            {
                "jsonrpc": "2.0",
                "id": "test-request",
                "error": {"code": -32001, "message": "Task not found"},
            },
            "missing-task-id",
        )


@mandatory_protocol
def test_tasks_cancel_valid(sut_client, created_task_id):
    """
    MANDATORY: A2A v1.0 §3.1.5. Cancel Task

    The A2A v1.0 specification requires all implementations to support
    CancelTask for canceling active tasks.
    This test works across all transport types (JSON-RPC, gRPC, REST).

    Failure Impact: Implementation is not A2A compliant

    Specification Reference: A2A v1.0 §3.1.5. Cancel Task
    """
    # Use transport-agnostic task cancellation
    resp = transport_cancel_task(sut_client, created_task_id)
    assert_cancel_response_valid(resp, created_task_id)


@mandatory_protocol
def test_tasks_cancel_nonexistent(sut_client):
    """
    MANDATORY: A2A v1.0 §3.1.5. Cancel Task

    The A2A v1.0 specification requires proper error handling when attempting
    to cancel a non-existent task. MUST return TaskNotFoundError (-32001).
    This test works across all transport types (JSON-RPC, gRPC, REST).

    Failure Impact: Implementation is not A2A v1.0 compliant

    Specification Reference: A2A v1.0 §3.1.5. Cancel Task
    """
    # Use transport-agnostic task cancellation for non-existent task
    resp = transport_cancel_task(sut_client, "nonexistent-task-id")

    # Should receive an error response
    assert not is_json_rpc_success_response(
        resp
    ), f"Expected error for non-existent task, got: {resp}"
    assert "error" in resp, f"Response should contain error field: {resp}"

    # Validate A2A v1.0 TaskNotFoundError code
    error_code = resp["error"].get("code")
    assert (
        error_code == -32001
    ), f"Expected TaskNotFoundError (-32001), got error code: {error_code}"
