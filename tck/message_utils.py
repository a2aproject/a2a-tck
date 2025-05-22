import uuid
from typing import Any, Dict, Optional, Union


def generate_request_id() -> str:
    return str(uuid.uuid4())

def make_json_rpc_request(
    method: str,
    params: Union[dict, list, None] = None,
    id: Union[str, int, None] = None,
) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params if params is not None else {},
        "id": id if id is not None else generate_request_id(),
    }

def is_json_rpc_success_response(resp: dict, expected_id: Union[str, int, None] = None) -> bool:
    if not isinstance(resp, dict):
        return False
    if resp.get("jsonrpc") != "2.0":
        return False
    if "result" not in resp:
        return False
    if expected_id is not None and resp.get("id") != expected_id:
        return False
    return True

def is_json_rpc_error_response(resp: dict, expected_id: Union[str, int, None] = None) -> bool:
    if not isinstance(resp, dict):
        return False
    if resp.get("jsonrpc") != "2.0":
        return False
    error = resp.get("error")
    if not isinstance(error, dict):
        return False
    if "code" not in error or "message" not in error:
        return False
    if expected_id is not None and resp.get("id") != expected_id:
        return False
    return True
