import json
import uuid

import pytest

from tck import message_utils
from tck.sut_client import SUTClient


@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()

@pytest.fixture
def text_message_params():
    """Create a basic text message params object"""
    return {
        "message": {
            "parts": [
                {
                    "kind": "text",
                    "text": "Hello from protocol violation test!"
                }
            ]
        }
    }

# Protocol Violation: Duplicate Request IDs
@pytest.mark.all  # Not a core test
def test_duplicate_request_ids(sut_client, text_message_params):
    """
    Test SUT's response to duplicate request IDs.
    
    Send two different requests with the same ID and verify the SUT handles this protocol violation correctly.
    """
    # Generate a fixed ID for both requests
    fixed_id = f"duplicate-{uuid.uuid4()}"
    
    # First request with the fixed ID
    first_req = message_utils.make_json_rpc_request(
        "message/send", 
        params=text_message_params,
        id=fixed_id
    )
    first_resp = sut_client.send_json_rpc(**first_req)
    assert message_utils.is_json_rpc_success_response(first_resp, expected_id=fixed_id)
    
    # Second request with the same ID but different params
    second_params = text_message_params.copy()
    second_params["message"]["parts"][0]["text"] = "This is a different message with the same ID"
    
    second_req = message_utils.make_json_rpc_request(
        "message/send", 
        params=second_params,
        id=fixed_id
    )
    second_resp = sut_client.send_json_rpc(**second_req)
    
    # Various SUTs might handle this differently:
    # 1. Reject with InvalidRequest error
    # 2. Accept and process normally (not ideal but possible)
    # 3. Recognize as a duplicate and return the same response
    
    # Just verify we got a valid JSON-RPC response (success or error)
    assert "jsonrpc" in second_resp
    assert "id" in second_resp and second_resp["id"] == fixed_id

# Protocol Violation: Malformed Version
@pytest.mark.all  # Not a core test
def test_invalid_jsonrpc_version(sut_client, text_message_params):
    """
    Test SUT's response to an invalid JSON-RPC version.
    
    Send a request with an incorrect jsonrpc field value and verify the SUT rejects it.
    """
    # Create a valid request first
    req = message_utils.make_json_rpc_request("message/send", params=text_message_params)
    
    # Modify the jsonrpc version to an invalid value
    req["jsonrpc"] = "1.0"  # Should be "2.0"
    
    # Send the malformed request
    resp = sut_client.send_json_rpc(**req)
    
    # SUT should reject with InvalidRequest error
    assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"])
    assert resp["error"]["code"] == -32600  # InvalidRequest

# Protocol Violation: Missing Required Field
@pytest.mark.all  # Not a core test
def test_missing_method_field(sut_client, text_message_params):
    """
    Test SUT's response to a request missing the method field.
    
    Send a request without the required method field and verify the SUT rejects it.
    """
    # Create a valid request first
    req = message_utils.make_json_rpc_request("message/send", params=text_message_params)
    
    # Remove the method field
    req.pop("method")
    
    # Send the malformed request
    resp = sut_client.send_json_rpc(**req)
    
    # SUT should reject with InvalidRequest error
    assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"])
    assert resp["error"]["code"] == -32600  # InvalidRequest

# Protocol Violation: Send raw invalid JSON
@pytest.mark.all  # Not a core test
def test_raw_invalid_json(sut_client):
    """
    Test SUT's response to raw invalid JSON.
    
    Send a request with invalid JSON syntax and verify the SUT rejects it.
    """
    # Create an intentionally invalid JSON string
    invalid_json = """{"jsonrpc": "2.0", "method": "message/send", "params": {"unclosed_object": true"""
    
    # Use the raw_send method to send invalid JSON
    status_code, response_text = sut_client.raw_send(invalid_json)
    
    # SUT should either:
    # 1. Respond with a 400 Bad Request status
    # 2. Or respond with a Parse Error JSON-RPC response
    
    if status_code == 400:
        # This is a valid HTTP-level rejection
        pass
    else:
        # Try to parse the response
        try:
            resp = json.loads(response_text)
            assert "error" in resp
            assert resp["error"]["code"] == -32700  # Parse error
        except json.JSONDecodeError:
            # If the response is not valid JSON, that's an issue
            pytest.fail("SUT response to invalid JSON is not a valid JSON or HTTP error")

# Add a raw_send method to SUTClient class to test raw invalid JSON
# This would need to be implemented in tck/sut_client.py like this:
"""
def raw_send(self, raw_data):
    '''Send raw data to the SUT endpoint without JSON validation.'''
    url = self.config.sut_url
    headers = {'Content-Type': 'application/json'}
    
    self.logger.info(f"Sending raw data to {url}: {raw_data}")
    
    try:
        response = requests.post(url, data=raw_data, headers=headers)
        self.logger.info(f"SUT responded with {response.status_code}: {response.text}")
        return response.status_code, response.text
    except requests.exceptions.RequestException as e:
        self.logger.error(f"HTTP request failed: {e}")
        raise
""" 