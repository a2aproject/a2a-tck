import pytest

from tck import message_utils
from tck.sut_client import SUTClient


@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()

@pytest.mark.all  # Not a core test as per requirements
def test_unsupported_part_kind(sut_client):
    """
    A2A JSON-RPC Spec: Business Logic Validation
    Test that the SUT properly rejects a message with an unsupported part kind.
    """
    # Create a message with an unsupported part kind
    params = {
        "message": {
            "parts": [
                {
                    "kind": "unsupported_kind",  # Invalid/unsupported kind
                    "text": "This should be rejected"
                }
            ]
        }
    }
    
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = sut_client.send_json_rpc(**req)
    
    # Expect either an error response or a task with failed state
    if message_utils.is_json_rpc_error_response(resp, expected_id=req["id"]):
        # Check if it's an InvalidParamsError or other error
        assert resp["error"]["code"] in {-32602, -32603}, "Expected InvalidParamsError or InternalError"
    else:
        # If not an error response, the task might be created but in a failed state
        assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
        task = resp["result"]
        assert task["status"].get("state") in {"failed", "error"}, "Task should be in failed state"

@pytest.mark.all  # Not a core test as per requirements
def test_invalid_file_part(sut_client):
    """
    A2A JSON-RPC Spec: Business Logic Validation
    Test that the SUT properly handles a file part with invalid URL or metadata.
    """
    # Create a message with a file part containing an invalid URL
    params = {
        "message": {
            "parts": [
                {
                    "kind": "file",
                    "file": {
                        "name": "test.txt",
                        "mimeType": "text/plain",
                        "url": "invalid://url.com/file.txt",  # Invalid URL
                        "sizeInBytes": 1024
                    }
                }
            ]
        }
    }
    
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = sut_client.send_json_rpc(**req)
    
    # The SUT might either reject with an error or accept and later fail the task
    if message_utils.is_json_rpc_error_response(resp, expected_id=req["id"]):
        # It's acceptable to reject with an error
        pass
    else:
        # If accepted, the task might be created in a working or failed state
        assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
        task = resp["result"]
        # Don't assert on the state here as it might be implementation-specific

@pytest.mark.all  # Not a core test as per requirements
def test_empty_message_parts(sut_client):
    """
    A2A JSON-RPC Spec: Business Logic Validation
    Test that the SUT properly handles a message with empty parts array.
    """
    # Create a message with empty parts array
    params = {
        "message": {
            "parts": []
        }
    }
    
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = sut_client.send_json_rpc(**req)
    
    # Expect an error response for empty parts
    assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"])
    assert resp["error"]["code"] == -32602, "Expected InvalidParamsError for empty parts"

@pytest.mark.all  # Not a core test as per requirements
def test_very_large_message(sut_client):
    """
    A2A JSON-RPC Spec: Business Logic Validation
    Test that the SUT properly handles a message with very large text content.
    """
    # Create a message with a very large text part
    large_text = "A" * 100000  # 100KB of text
    params = {
        "message": {
            "parts": [
                {
                    "kind": "text",
                    "text": large_text
                }
            ]
        }
    }
    
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = sut_client.send_json_rpc(**req)
    
    # The SUT might either:
    # 1. Accept the message and handle it (success)
    # 2. Reject it with an error (e.g., payload too large)
    # 3. Accept but fail the task
    
    # Don't make strict assertions here, as the behavior is implementation-specific
    # Just make sure we get a valid JSON-RPC response
    assert "jsonrpc" in resp
    assert "id" in resp and resp["id"] == req["id"] 