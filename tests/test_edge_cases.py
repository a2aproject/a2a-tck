import logging
import uuid

import pytest

from tck import message_utils
from tck.sut_client import SUTClient

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()

# Edge Case: Very Long String
@pytest.mark.all  # Not a core test
def test_very_long_string(sut_client):
    """
    Test SUT's handling of a message with a very long text string.
    """
    # Create a message with a very long text (1MB)
    long_text = "A" * (1024 * 1024)  # 1MB string
    params = {
        "message": {
            "messageId": "test-long-string-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "type": "text",
                    "text": long_text
                }
            ]
        }
    }
    
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = sut_client.send_json_rpc(**req)
    
    # The SUT may handle this in different ways:
    # 1. Accept and process it (unlikely but possible)
    # 2. Reject with an HTTP error (413 Payload Too Large)
    # 3. Reject with a JSON-RPC InvalidParams error
    
    # We just verify we got a response of some kind
    assert "jsonrpc" in resp
    assert "id" in resp and resp["id"] == req["id"]

# Edge Case: Empty Arrays
@pytest.mark.all  # Not a core test
def test_empty_arrays(sut_client):
    """
    Test SUT's handling of empty arrays in parameters.
    """
    # Empty parts array (should be rejected)
    params = {
        "message": {
            "messageId": "test-empty-array-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": []
        }
    }
    
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = sut_client.send_json_rpc(**req)
    
    # The SUT should reject this with InvalidParams
    assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"])
    assert resp["error"]["code"] == -32602  # InvalidParams

# Edge Case: Null Values in Optional Fields
@pytest.mark.all  # Not a core test
def test_null_optional_fields(sut_client):
    """
    Test SUT's handling of null values in optional fields.
    """
    params = {
        "message": {
            "messageId": "test-null-fields-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "type": "text",
                    "text": "Hello with null fields"
                }
            ],
            "taskId": None,       # Explicitly null
            "contextId": None,    # Explicitly null
            "metadata": None      # Explicitly null
        }
    }
    
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = sut_client.send_json_rpc(**req)
    
    # The SUT should either:
    # 1. Treat nulls as missing fields and create a new task
    # 2. Reject with InvalidParams if nulls aren't allowed
    
    if message_utils.is_json_rpc_success_response(resp, expected_id=req["id"]):
        # If success, should create a new task
        assert "id" in resp["result"]
    else:
        # If error, should be InvalidParams
        assert resp["error"]["code"] == -32602

# Edge Case: Unexpected JSON Types
@pytest.mark.all  # Not a core test
def test_unexpected_json_types(sut_client):
    """
    Test SUT's handling of unexpected but valid JSON types in parameters.
    """

    params = {
        "taskId": 12345  # Integer instead of expected string
    }
    
    req = message_utils.make_json_rpc_request("tasks/get", params=params)
    resp = sut_client.send_json_rpc(**req)
    
    # The SUT should either:
    # 1. Convert the integer to string and process it (good behavior)
    # 2. Reject with InvalidParams (strict but acceptable)
    
    # Just verify we got a valid response
    assert "jsonrpc" in resp
    assert "id" in resp and resp["id"] == req["id"]

# Edge Case: Extra Fields
@pytest.mark.all  # Not a core test
def test_extra_fields(sut_client):
    """
    Test SUT's handling of extra, unexpected fields in parameters.
    """
    params = {
        "message": {
            "messageId": "test-extra-fields-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "type": "text",
                    "text": "Message with extra fields"
                }
            ],
            "_extra_field": "This field is not in the spec",
            "_debug_info": {
                "client_version": "1.0.0",
                "timestamp": 1234567890
            }
        }
    }
    
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = sut_client.send_json_rpc(**req)
    
    # The SUT should either:
    # 1. Ignore the extra fields and process normally (good behavior)
    # 2. Reject with InvalidParams (strict but acceptable)
    
    # Just verify we got a valid response of some kind
    assert "jsonrpc" in resp
    assert "id" in resp and resp["id"] == req["id"]

# Edge Case: Unicode and Special Characters
@pytest.mark.all  # Not a core test
def test_unicode_and_special_chars(sut_client):
    """
    Test SUT's handling of Unicode and special characters in parameters.
    """
    params = {
        "message": {
            "messageId": "test-unicode-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "type": "text",
                    "text": "Unicode: 你好, здравствуйте, مرحبا, こんにちは\nControl chars: \t\b\f\r\n"
                }
            ]
        }
    }
    
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = sut_client.send_json_rpc(**req)
    
    # The SUT should handle Unicode correctly
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    
    # Get the task to verify it was stored correctly
    task_id = resp["result"]["id"]
    get_req = message_utils.make_json_rpc_request("tasks/get", params={"id": task_id})
    get_resp = sut_client.send_json_rpc(**get_req)
    
    assert message_utils.is_json_rpc_success_response(get_resp, expected_id=get_req["id"])

# Edge Case: Boundary Values
@pytest.mark.all  # Not a core test
def test_boundary_values(sut_client):
    """
    Test SUT's handling of boundary values in parameters.
    """
    # Test with minimum/maximum values for historyLength
    task_id = _create_simple_task(sut_client)
    
    # Very large historyLength (e.g., int32 max)
    large_history_req = message_utils.make_json_rpc_request(
        "tasks/get", 
        params={"id": task_id, "historyLength": 2147483647}
    )
    large_history_resp = sut_client.send_json_rpc(**large_history_req)
    
    # Very small historyLength (e.g., 0)
    zero_history_req = message_utils.make_json_rpc_request(
        "tasks/get", 
        params={"id": task_id, "historyLength": 0}
    )
    zero_history_resp = sut_client.send_json_rpc(**zero_history_req)
    
    # Negative historyLength (invalid)
    neg_history_req = message_utils.make_json_rpc_request(
        "tasks/get", 
        params={"id": task_id, "historyLength": -1}
    )
    neg_history_resp = sut_client.send_json_rpc(**neg_history_req)
    
    # Check that positive values are accepted
    assert message_utils.is_json_rpc_success_response(large_history_resp, expected_id=large_history_req["id"])
    assert message_utils.is_json_rpc_success_response(zero_history_resp, expected_id=zero_history_req["id"])
    
    # Negative should be rejected
    assert message_utils.is_json_rpc_error_response(neg_history_resp, expected_id=neg_history_req["id"])

# Helper function to create a simple task for testing
def _create_simple_task(sut_client):
    """Create a simple task and return its ID."""
    params = {
        "message": {
            "messageId": "test-simple-task-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "type": "text",
                    "text": f"Simple task for edge case testing {uuid.uuid4()}"
                }
            ]
        }
    }
    
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = sut_client.send_json_rpc(**req)
    
    if not message_utils.is_json_rpc_success_response(resp, expected_id=req["id"]):
        pytest.skip("Failed to create task for edge case test")
        
    return resp["result"]["id"] 