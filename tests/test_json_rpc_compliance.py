import pytest
import requests

from tck import message_utils
from tck.sut_client import SUTClient


@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()

@pytest.mark.core
def test_rejects_malformed_json(sut_client):
    """
    JSON-RPC 2.0 Spec: Parse error (-32700)
    The SUT should reject syntactically invalid JSON with HTTP 400 or JSON-RPC error -32700.
    """
    malformed_json = '{"jsonrpc": "2.0", "method": "message/send", "params": {"foo": "bar"}'  # missing closing }
    url = sut_client.base_url
    headers = {"Content-Type": "application/json"}
    # We expect a network error or HTTP error due to malformed JSON
    response = requests.post(url, data=malformed_json, headers=headers, timeout=10)
    # If the SUT returns a JSON-RPC error, check for code -32700

    resp_json = response.json()
    assert resp_json.get("error", {}).get("code") == -32700  # Spec: JSONParseError
    
@pytest.mark.core
@pytest.mark.parametrize("invalid_request,expected_code", [
    ({"method": "message/send", "params": {}}, -32600),  # missing jsonrpc
    ({"jsonrpc": "2.0", "params": {},}, -32601),         # missing method
    ({"jsonrpc": "2.0", "method": "message/send", "params": {}, "id": {"bad": "type"}}, -32600),  # invalid id type
    ({"jsonrpc": "2.0", "method": "message/send", "params": "not_a_dict"}, -32602),  # invalid params type
])
def test_rejects_invalid_json_rpc_requests(sut_client, invalid_request, expected_code):
    """
    JSON-RPC 2.0 Spec: Invalid Request (-32600), Invalid Params (-32602)
    The SUT should reject structurally invalid JSON-RPC requests with the correct error code.
    """
    url = sut_client.base_url
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=invalid_request, headers=headers, timeout=10)
    assert response.status_code == 200  # JSON-RPC errors are returned with 200
    resp_json = response.json()
    assert "error" in resp_json
    assert resp_json["error"]["code"] == expected_code

@pytest.mark.core
def test_rejects_unknown_method(sut_client):
    """
    JSON-RPC 2.0 Spec: Method not found (-32601)
    The SUT should reject requests with undefined method names with error code -32601.
    """
    req = message_utils.make_json_rpc_request("nonexistent/method", params={})
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert resp["error"]["code"] == -32601  # Spec: MethodNotFoundError
    assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"])

@pytest.mark.core
def test_rejects_invalid_params(sut_client):
    """
    JSON-RPC 2.0 Spec: Invalid Params (-32602)
    The SUT should reject requests with invalid parameters with error code -32602.
    """
    req = message_utils.make_json_rpc_request("message/send", params={"message": {"parts": "invalid"}})
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert resp["error"]["code"] == -32602  # Spec: InvalidParamsError