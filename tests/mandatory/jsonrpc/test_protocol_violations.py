import json
import logging
import uuid

import pytest

from tck import message_utils
from tck.sut_client import SUTClient
from tests.markers import mandatory_jsonrpc


logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()


@pytest.fixture
def text_message_params():
    """Create a basic text message params object"""
    return {
        "message": {
            "kind": "message",
            "messageId": "test-protocol-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [{"kind": "text", "text": "Hello from protocol violation test!"}],
        }
    }


@mandatory_jsonrpc
def test_duplicate_request_ids(sut_client, text_message_params):
    """MANDATORY: JSON-RPC 2.0 Specification §4.1 - Request ID Uniqueness

    JSON-RPC 2.0 requires proper handling of request IDs. While the specification
    doesn't explicitly mandate rejecting duplicates, proper implementations
    should handle duplicate IDs consistently.

    Failure Impact: Implementation may not follow JSON-RPC 2.0 ID semantics
    """
    # Generate a fixed ID for both requests
    fixed_id = f"duplicate-{uuid.uuid4()}"

    # First request with the fixed ID
    first_req = message_utils.make_json_rpc_request("message/send", params=text_message_params, id=fixed_id)
    first_resp = sut_client.send_json_rpc(**first_req)
    assert message_utils.is_json_rpc_success_response(first_resp, expected_id=fixed_id)

    # Second request with the same ID but different params
    second_params = text_message_params.copy()
    second_params["message"]["parts"][0]["text"] = "This is a different message with the same ID"

    second_req = message_utils.make_json_rpc_request("message/send", params=second_params, id=fixed_id)
    second_resp = sut_client.send_json_rpc(**second_req)

    # Various SUTs might handle this differently:
    # 1. Reject with InvalidRequest error
    # 2. Accept and process normally (not ideal but possible)
    # 3. Recognize as a duplicate and return the same response

    # Just verify we got a valid JSON-RPC response (success or error)
    assert "jsonrpc" in second_resp
    assert "id" in second_resp and second_resp["id"] == fixed_id


@mandatory_jsonrpc
def test_invalid_jsonrpc_version(sut_client, text_message_params):
    """MANDATORY: JSON-RPC 2.0 Specification §4.1 - Version Field Validation

    The JSON-RPC 2.0 specification states the jsonrpc field MUST be exactly "2.0".
    The server MUST reject requests with invalid jsonrpc versions.

    Failure Impact: Implementation is not JSON-RPC 2.0 compliant
    """
    # Create a valid request first
    req = message_utils.make_json_rpc_request("message/send", params=text_message_params)

    # Modify the jsonrpc version to an invalid value (violates JSON-RPC 2.0 MUST requirement)
    req["jsonrpc"] = "1.0"  # Should be "2.0"

    # Send the malformed request using raw JSON-RPC method
    resp = sut_client.send_raw_json_rpc(req)

    # Per JSON-RPC 2.0 spec, this MUST be rejected with InvalidRequest error
    assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"]), (
        f"SUT MUST reject requests with invalid jsonrpc version per JSON-RPC 2.0 spec, but got: {resp}"
    )
    assert resp["error"]["code"] == -32600, (
        f"Expected InvalidRequest error code -32600, but got: {resp['error']['code']} (Spec: InvalidRequestError)"
    )


@mandatory_jsonrpc
def test_missing_method_field(sut_client, text_message_params):
    """MANDATORY: JSON-RPC 2.0 Specification §4.1 - Required Method Field

    The JSON-RPC 2.0 specification states the method field is REQUIRED.
    The server MUST reject requests missing required fields.

    Failure Impact: Implementation is not JSON-RPC 2.0 compliant
    """
    # Create a valid request first
    req = message_utils.make_json_rpc_request("message/send", params=text_message_params)
    print(f"req: {req}")

    # Remove the method field (violates JSON-RPC 2.0 MUST requirement)
    req.pop("method")
    print(f"req: {req}")

    # Send the malformed request using raw JSON-RPC method
    resp = sut_client.send_raw_json_rpc(req)

    # Per JSON-RPC 2.0 spec, this MUST be rejected with InvalidRequest error
    assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"]), (
        f"SUT MUST reject requests missing required 'method' field per JSON-RPC 2.0 spec, but got: {resp}"
    )
    assert resp["error"]["code"] == -32600, (
        f"Expected InvalidRequest error code -32600, but got: {resp['error']['code']} (Spec: InvalidRequestError)"
    )


@mandatory_jsonrpc
def test_raw_invalid_json(sut_client):
    """MANDATORY: A2A Specification §4.1 JSON-RPC 2.0 Compliance - Parse Error Handling

    Tests A2A Specification requirement that implementations MUST use JSON-RPC 2.0.
    The JSON-RPC 2.0 specification requires servers to reject
    syntactically invalid JSON with Parse Error (-32700).

    Failure Impact: Implementation is not A2A compliant
    Fix Suggestion: Implement proper JSON parsing and error handling per JSON-RPC 2.0

    Asserts:
        - Invalid JSON is rejected with appropriate error codes
        - Error responses follow JSON-RPC 2.0 specification
        - Implementation maintains A2A compliance requirements
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
            assert resp["error"]["code"] == -32700, (
                f"Expected JSONParseError error code -32700, but got: {resp['error']['code']} (Spec: JSONParseError)"
            )
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
