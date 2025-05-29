import pytest
import requests

from tck import message_utils
from tck.sut_client import SUTClient
from tests.markers import mandatory_jsonrpc


@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()

@mandatory_jsonrpc
def test_rejects_malformed_json(sut_client):
    """
    MANDATORY: JSON-RPC 2.0 Specification §4.2 - Parse Error
    
    The server MUST reject syntactically invalid JSON with error code -32700.
    This is a hard requirement for JSON-RPC compliance.
    
    Failure Impact: Implementation is not JSON-RPC 2.0 compliant
    """
    malformed_json = '{"jsonrpc": "2.0", "method": "message/send", "params": {"foo": "bar"}'  # missing closing }
    url = sut_client.base_url
    headers = {"Content-Type": "application/json"}
    # We expect a network error or HTTP error due to malformed JSON
    response = requests.post(url, data=malformed_json, headers=headers, timeout=10)
    # If the SUT returns a JSON-RPC error, check for code -32700

    resp_json = response.json()
    assert resp_json.get("error", {}).get("code") == -32700  # Spec: JSONParseError
    
@mandatory_jsonrpc
@pytest.mark.parametrize("invalid_request,expected_code", [
    ({"method": "message/send", "params": {}}, -32600),  # missing jsonrpc
    ({"jsonrpc": "2.0", "params": {},}, -32601),         # missing method
    ({"jsonrpc": "2.0", "method": "message/send", "params": {}, "id": {"bad": "type"}}, -32600),  # invalid id type
    ({"jsonrpc": "2.0", "method": "message/send", "params": "not_a_dict"}, -32602),  # invalid params type
])
def test_rejects_invalid_json_rpc_requests(sut_client, invalid_request, expected_code):
    """
    MANDATORY: JSON-RPC 2.0 Specification §4.1 & §4.3 - Request Structure
    
    The server MUST have required fields (jsonrpc, method) and MUST return
    proper error codes for invalid requests: -32600 (Invalid Request), 
    -32601 (Method not found), -32602 (Invalid params).
    
    Failure Impact: Implementation is not JSON-RPC 2.0 compliant
    """
    url = sut_client.base_url
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=invalid_request, headers=headers, timeout=10)
    assert response.status_code == 200  # JSON-RPC errors are returned with 200
    resp_json = response.json()
    assert "error" in resp_json
    assert resp_json["error"]["code"] == expected_code

@mandatory_jsonrpc
def test_rejects_unknown_method(sut_client):
    """
    MANDATORY: JSON-RPC 2.0 Specification §4.3 - Method Not Found
    
    The server MUST reject requests with undefined method names 
    with error code -32601 (Method not found).
    
    Failure Impact: Implementation is not JSON-RPC 2.0 compliant
    """
    req = message_utils.make_json_rpc_request("nonexistent/method", params={})
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert resp["error"]["code"] == -32601  # Spec: MethodNotFoundError
    assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"])

@mandatory_jsonrpc
def test_rejects_invalid_params(sut_client):
    """
    MANDATORY: JSON-RPC 2.0 Specification §4.3 - Invalid Parameters
    
    The server MUST reject requests with invalid parameters 
    with error code -32602 (Invalid params).
    
    Failure Impact: Implementation is not JSON-RPC 2.0 compliant
    """
    req = message_utils.make_json_rpc_request("message/send", params={"message": {"parts": "invalid"}})
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert resp["error"]["code"] == -32602  # Spec: InvalidParamsError