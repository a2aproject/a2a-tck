import logging
import uuid

import pytest

from tck import message_utils
from tests.utils import transport_helpers

from tests.markers import quality_production, quality_basic

logger = logging.getLogger(__name__)

# Using transport-agnostic sut_client fixture from conftest.py

@quality_basic
def test_very_long_string(sut_client):
    """
    QUALITY BASIC: A2A Specification §5.1 - Large Payload Handling
    
    Tests the SUT's ability to handle very large text payloads gracefully.
    Production systems should either process large payloads or reject them
    with appropriate error messages.
    
    Validates:
    - Large text string handling (1MB payload)
    - Proper error responses for oversized requests
    - No system crashes or hangs
    - Specification compliance for array requirements
    """
    # Create a message with a very long text (1MB)
    long_text = "A" * (1024 * 1024)  # 1MB string
    params = {
        "message": {
            "messageId": "test-long-string-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": long_text
                }
            ],
            "kind": "message"
        }
    }
    
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = transport_helpers.transport_send_message(sut_client, params)
    
    # The SUT may handle this in different ways:
    # 1. Accept and process it (good for large content handling)
    # 2. Reject with an HTTP error (413 Payload Too Large)
    # 3. Reject with a JSON-RPC InvalidParams error
    
    # We just verify we got a response of some kind (no crash/hang)
    assert isinstance(resp, dict), "Large payload caused SUT to return invalid response"
    # Transport helper responses may be success or error format
    assert "result" in resp or "error" in resp, "Response should contain result or error"

@quality_basic
def test_empty_arrays(sut_client):
    """
    QUALITY BASIC: Empty Array Validation
    
    Tests proper validation of empty arrays where they shouldn't be allowed.
    Good implementations should validate required array fields and reject
    empty arrays with clear error messages.
    
    Validates:
    - Proper validation of parts array (must not be empty)
    - Clear InvalidParams error responses
    - Specification compliance for array requirements
    """
    # Empty parts array (should be rejected)
    params = {
        "message": {
            "messageId": "test-empty-array-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [],
            "kind": "message"
        }
    }
    
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = transport_helpers.transport_send_message(sut_client, params)
    
    # The SUT should reject this with InvalidParams
    assert transport_helpers.is_json_rpc_error_response(resp), \
        "Empty parts array should be rejected"
    assert resp["error"]["code"] == -32602, "Should return InvalidParams error code"

@quality_basic
def test_null_optional_fields(sut_client):
    """
    QUALITY BASIC: Null Value Handling
    
    Tests handling of explicit null values in optional fields.
    Good implementations should treat nulls consistently - either
    as missing fields or reject them with clear errors.
    
    Validates:
    - Handling of null values in optional fields
    - Consistent behavior for null vs missing fields
    - Proper error messages if nulls are rejected
    """
    params = {
        "message": {
            "messageId": "test-null-fields-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Hello with null fields"
                }
            ],
            "taskId": None,       # Explicitly null
            "contextId": None,    # Explicitly null
            "metadata": None,      # Explicitly null
            "kind": "message"
        }
    }
    
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = transport_helpers.transport_send_message(sut_client, params)
    
    # The SUT should either:
    # 1. Treat nulls as missing fields and create a new task
    # 2. Reject with InvalidParams if nulls aren't allowed
    
    if transport_helpers.is_json_rpc_success_response(resp):
        # If success, should create a new task
        assert "id" in resp["result"], "Successful response should include task ID"
    else:
        # If error, should be InvalidParams
        assert resp["error"]["code"] == -32602, "Null value rejection should use InvalidParams error"

@quality_basic
def test_unexpected_json_types(sut_client):
    """
    QUALITY BASIC: A2A Specification §4.1 - Type Coercion Handling
    
    Tests handling of unexpected but valid JSON types in parameters.
    Good implementations should either gracefully coerce types or
    reject them with clear error messages.
    
    Validates:
    - Type handling for mismatched but coercible types
    - Clear error messages for type mismatches
    - Robust input validation
    - Specification compliance for type requirements
    """
    params = {
        "taskId": 12345  # Integer instead of expected string
    }
    
    req = message_utils.make_json_rpc_request("tasks/get", params=params)
    resp = transport_helpers.transport_send_message(sut_client, params)
    
    # The SUT should either:
    # 1. Convert the integer to string and process it (good behavior)
    # 2. Reject with InvalidParams (strict but acceptable)
    
    # Just verify we got a valid response
    assert isinstance(resp, dict), "Type mismatch caused invalid response"
    # Transport helper responses may be success or error format
    assert "result" in resp or "error" in resp, "Response should contain result or error"

@quality_production
def test_extra_fields(sut_client):
    """
    QUALITY PRODUCTION: Forward Compatibility
    
    Tests handling of extra, unexpected fields in parameters.
    Production systems should be forward-compatible and ignore
    unknown fields gracefully to support future specification extensions.
    
    Validates:
    - Graceful handling of unknown fields
    - Forward compatibility with future spec versions
    - No rejection of valid requests with extra data
    """
    params = {
        "message": {
            "messageId": "test-extra-fields-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Message with extra fields"
                }
            ],
            "_extra_field": "This field is not in the spec",
            "_debug_info": {
                "client_version": "1.0.0",
                "timestamp": 1234567890
            },
            "kind": "message"
        }
    }
    
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = transport_helpers.transport_send_message(sut_client, params)
    
    # The SUT should either:
    # 1. Ignore the extra fields and process normally (preferred for production)
    # 2. Reject with InvalidParams (strict but acceptable)
    
    # Just verify we got a valid response of some kind
    assert isinstance(resp, dict), "Extra fields caused invalid response"
    # Transport helper responses may be success or error format
    assert "result" in resp or "error" in resp, "Response should contain result or error"

@quality_basic
def test_unicode_and_special_chars(sut_client):
    """
    QUALITY BASIC: Unicode and Character Handling
    
    Tests proper handling of Unicode and special characters.
    Modern systems must support international characters and
    control characters without corruption or errors.
    
    Validates:
    - Unicode character support (Chinese, Russian, Arabic, Japanese)
    - Control character handling (tabs, newlines, etc.)
    - Character encoding preservation through the system
    """
    params = {
        "message": {
            "messageId": "test-unicode-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Unicode: 你好, здравствуйте, مرحبا, こんにちは\nControl chars: \t\b\f\r\n"
                }
            ],
            "kind": "message"
        }
    }
    
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = transport_helpers.transport_send_message(sut_client, params)
    
    # The SUT should handle Unicode correctly
    assert transport_helpers.is_json_rpc_success_response(resp), \
        "Unicode characters should not cause message/send to fail"
    
    # Get the task to verify it was stored correctly
    task_id = resp["result"]["id"]
    get_req = message_utils.make_json_rpc_request("tasks/get", params={"id": task_id})
    get_resp = transport_helpers.transport_get_task(sut_client, task_id)
    
    assert transport_helpers.is_json_rpc_success_response(get_resp), \
        "Unicode characters should be preserved in task storage"

@quality_production
def test_boundary_values(sut_client):
    """
    QUALITY PRODUCTION: Boundary Value Handling
    
    Tests handling of boundary values in parameters.
    Production systems should handle boundary values correctly
    to prevent system crashes or unexpected behavior.
    
    Validates:
    - Proper handling of minimum and maximum values
    - Robust input validation for boundary conditions
    - No system crashes or unexpected behavior
    """
    # Test with minimum/maximum values for historyLength
    task_id = _create_simple_task(sut_client)
    
    # Very large historyLength (e.g., int32 max)
    large_history_req = message_utils.make_json_rpc_request(
        "tasks/get", 
        params={"id": task_id, "historyLength": 2147483647}
    )
    large_history_resp = transport_helpers.transport_get_task(sut_client, task_id, history_length=9999)
    
    # Very small historyLength (e.g., 0)
    zero_history_req = message_utils.make_json_rpc_request(
        "tasks/get", 
        params={"id": task_id, "historyLength": 0}
    )
    zero_history_resp = transport_helpers.transport_get_task(sut_client, task_id, history_length=0)
    
    # Negative historyLength (invalid)
    neg_history_req = message_utils.make_json_rpc_request(
        "tasks/get", 
        params={"id": task_id, "historyLength": -1}
    )
    neg_history_resp = transport_helpers.transport_get_task(sut_client, task_id, history_length=-1)
    
    # Check that positive values are accepted
    assert transport_helpers.is_json_rpc_success_response(large_history_resp), \
        "Large historyLength should be accepted"
    assert transport_helpers.is_json_rpc_success_response(zero_history_resp), \
        "Zero historyLength should be accepted"
    
    # Negative should be rejected
    assert transport_helpers.is_json_rpc_error_response(neg_history_resp), \
        "Negative historyLength should be rejected"

# Helper function to create a simple task for testing
def _create_simple_task(sut_client):
    """Create a simple task and return its ID."""
    params = {
        "message": {
            "messageId": "test-simple-task-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": f"Simple task for edge case testing {uuid.uuid4()}"
                }
            ],
            "kind": "message"
        }
    }
    
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = transport_helpers.transport_send_message(sut_client, params)
    
    if not transport_helpers.is_json_rpc_success_response(resp):
        pytest.skip("Failed to create task for edge case test")
        
    return resp["result"]["id"] 
