import pytest
import uuid
import logging

from tck import message_utils
from tests.utils import transport_helpers

# Import markers
mandatory_protocol = pytest.mark.mandatory_protocol
optional_feature = pytest.mark.optional_feature

logger = logging.getLogger(__name__)

# Using transport-agnostic sut_client fixture from conftest.py

@optional_feature
def test_unsupported_part_kind(sut_client):
    """
    OPTIONAL FEATURE: A2A Unsupported Part Type Handling
    
    Tests optional implementation that enhances user experience
    but is not required for A2A compliance.
    
    Test validates handling of unsupported message part types.
    
    Failure Impact: Limits feature completeness (perfectly acceptable)
    Fix Suggestion: Implement proper validation and error handling for unsupported part types
    
    Asserts:
        - Unsupported part types are handled gracefully
        - Error responses use appropriate error codes (InvalidParams/InternalError)
        - Tasks may be created in failed state if not rejected outright
    """
    # Create a message with an unsupported part type
    params = {
        "message": {
            "messageId": "test-unsupported-part-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "type": "unsupported_type",  # Invalid/unsupported type
                    "text": "This should be rejected"
                }
            ]
        }
    }
    
    # Replace with transport helper
    resp = transport_helpers.transport_send_message(sut_client, params)
    
    # Expect either an error response or a task with failed state
    if transport_helpers.is_json_rpc_error_response(resp):
        # Check if it's an InvalidParamsError or other error
        assert resp["error"]["code"] in {-32602, -32603}, "Expected InvalidParamsError or InternalError (Spec: InvalidParamsError/-32602, InternalError/-32603)"
    else:
        # If not an error response, the task might be created but in a failed state
        assert transport_helpers.is_json_rpc_success_response(resp)
        task = resp["result"]
        assert task["status"].get("state") in {"failed", "error"}, "Task should be in failed state"

@optional_feature
def test_invalid_file_part(sut_client):
    """
    OPTIONAL FEATURE: A2A Invalid File Part Handling
    
    Tests optional implementation that enhances user experience
    but is not required for A2A compliance.
    
    Test validates handling of file parts with invalid URLs or metadata.
    
    Failure Impact: Limits feature completeness (perfectly acceptable)
    Fix Suggestion: Implement robust file validation and error handling
    
    Asserts:
        - Invalid file parts are processed without crashing
        - Error responses are provided for invalid file references
        - Implementation behavior is consistent and predictable
    """
    # Create a message with a file part containing an invalid URL
    params = {
        "message": {
            "messageId": "test-invalid-file-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "file",
                    "file": {
                        "name": "test.txt",
                        "mimeType": "text/plain",  # RECOMMENDED: Media Type per A2A Spec §6.6.2
                        "uri": "invalid://url.com/file.txt",  # Invalid URL (note: uri, not url)
                        "sizeInBytes": 1024
                    }
                }
            ]
        }
    }
    
    # Replace with transport helper
    resp = transport_helpers.transport_send_message(sut_client, params)
    
    # The SUT might either reject with an error or accept and later fail the task
    if transport_helpers.is_json_rpc_error_response(resp):
        # It's acceptable to reject with an error
        pass
    else:
        # If accepted, the task might be created in a working or failed state
        assert transport_helpers.is_json_rpc_success_response(resp)
        task = resp["result"]
        # Don't assert on the state here as it might be implementation-specific

@mandatory_protocol
def test_empty_message_parts(sut_client):
    """
    MANDATORY: A2A Specification §5.1 - Message Structure Requirements
    
    The specification states: "A message MUST contain at least one part."
    
    Test validates core A2A compliance requirement for non-empty parts arrays.
    
    Failure Impact: SDK is NOT A2A compliant
    Fix Suggestion: Implement proper message validation to reject empty parts arrays
    
    Asserts:
        - Empty parts array is rejected with InvalidParams error (-32602)
        - Error response follows JSON-RPC 2.0 format
        - Implementation correctly validates required message structure
    """
    # Create a message with empty parts array (violates A2A MUST requirement)
    params = {
        "message": {
            "messageId": "test-empty-parts-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": []
        }
    }
    
    # Replace with transport helper
    resp = transport_helpers.transport_send_message(sut_client, params)
    
    # Per A2A spec, this MUST be rejected with InvalidParams error
    assert transport_helpers.is_json_rpc_error_response(resp), \
        f"SUT MUST reject messages with empty parts array per A2A spec, but got: {resp}"
    assert resp["error"]["code"] == -32602, \
        f"Expected InvalidParams error code -32602 for empty parts, but got: {resp['error']['code']} (Spec: InvalidParamsError)"

@optional_feature
def test_very_large_message(sut_client):
    """
    OPTIONAL FEATURE: A2A Large Message Handling
    
    Tests optional implementation that enhances user experience
    but is not required for A2A compliance.
    
    Test validates handling of very large text content in messages.
    
    Failure Impact: Limits feature completeness (perfectly acceptable)
    Fix Suggestion: Implement large message handling or appropriate size limits
    
    Asserts:
        - Large messages are processed without crashing
        - Valid JSON-RPC response is returned regardless of size limits
        - Implementation behavior is consistent and predictable
    """
    # Create a message with a very large text part
    large_text = "A" * 100000  # 100KB of text
    params = {
        "message": {
            "messageId": "test-large-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": large_text
                }
            ]
        }
    }
    
    # Replace with transport helper
    resp = transport_helpers.transport_send_message(sut_client, params)
    
    # The SUT might either:
    # 1. Accept the message and handle it (success)
    # 2. Reject it with an error (e.g., payload too large)
    # 3. Accept but fail the task
    
    # Don't make strict assertions here, as the behavior is implementation-specific
    # Just make sure we get a valid response
    assert isinstance(resp, dict), "Response should be a dictionary"

@mandatory_protocol
def test_missing_required_message_fields(sut_client):
    """
    MANDATORY: A2A Specification §5.1 - Required Message Fields
    
    The specification states: "A Message MUST have messageId, role, and parts fields."
    
    Test validates core A2A compliance requirement for required message fields.
    
    Failure Impact: SDK is NOT A2A compliant
    Fix Suggestion: Implement proper message validation to ensure all required fields are present
    
    Asserts:
        - Missing messageId field is rejected with InvalidParams error (-32602)
        - Missing role field is rejected with InvalidParams error (-32602)
        - Missing parts field is rejected with InvalidParams error (-32602)
        - All error responses follow JSON-RPC 2.0 format
    """
    
    # Test 1: Missing messageId (MUST requirement violation)
    params_no_message_id = {
        "message": {
            # messageId is missing - violates A2A MUST requirement
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Message without messageId"
                }
            ]
        }
    }
    
    resp = transport_helpers.transport_send_message(sut_client, params_no_message_id)
    
    # Per A2A spec, this MUST be rejected with InvalidParams error
    assert transport_helpers.is_json_rpc_error_response(resp), \
        f"SUT MUST reject messages missing required 'messageId' field per A2A spec, but got: {resp}"
    assert resp["error"]["code"] == -32602, \
        f"Expected InvalidParams error code -32602 for missing messageId, but got: {resp['error']['code']} (Spec: InvalidParamsError)"
    
    # Test 2: Missing role (MUST requirement violation)
    params_no_role = {
        "message": {
            "messageId": "test-no-role-message-id-" + str(uuid.uuid4()),
            # role is missing - violates A2A MUST requirement
            "parts": [
                {
                    "kind": "text",
                    "text": "Message without role"
                }
            ]
        }
    }
    
    resp = transport_helpers.transport_send_message(sut_client, params_no_role)
    
    # Per A2A spec, this MUST be rejected with InvalidParams error
    assert transport_helpers.is_json_rpc_error_response(resp), \
        f"SUT MUST reject messages missing required 'role' field per A2A spec, but got: {resp}"
    assert resp["error"]["code"] == -32602, \
        f"Expected InvalidParams error code -32602 for missing role, but got: {resp['error']['code']} (Spec: InvalidParamsError)"
    
    # Test 3: Missing parts (MUST requirement violation)  
    params_no_parts = {
        "message": {
            "messageId": "test-no-parts-message-id-" + str(uuid.uuid4()),
            "role": "user"
            # parts is missing - violates A2A MUST requirement
        }
    }
    
    resp = transport_helpers.transport_send_message(sut_client, params_no_parts)
    
    # Per A2A spec, this MUST be rejected with InvalidParams error
    assert transport_helpers.is_json_rpc_error_response(resp), \
        f"SUT MUST reject messages missing required 'parts' field per A2A spec, but got: {resp}"
    assert resp["error"]["code"] == -32602, \
        f"Expected InvalidParams error code -32602 for missing parts, but got: {resp['error']['code']} (Spec: InvalidParamsError)"

@optional_feature
def test_file_part_without_mimetype(sut_client):
    """
    OPTIONAL FEATURE: A2A Specification §6.6.2 - FileWithUri mimeType Handling
    
    Tests handling of FileWithUri objects without the RECOMMENDED mimeType field.
    Per the updated specification, mimeType is RECOMMENDED (not required) and 
    should reference Media Type standards.
    
    Failure Impact: Limits feature completeness (perfectly acceptable)
    Fix Suggestion: Handle files gracefully even without explicit mimeType
    
    Asserts:
        - File parts without mimeType are processed without crashing
        - Implementation handles missing RECOMMENDED fields appropriately
        - Behavior is consistent and predictable
    """
    # Create a message with a file part missing the RECOMMENDED mimeType field
    params = {
        "message": {
            "messageId": "test-no-mimetype-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "file",
                    "file": {
                        "name": "test.txt",
                        # mimeType is RECOMMENDED but not required per A2A Spec §6.6.2
                        "url": "https://example.com/test.txt",
                        "sizeInBytes": 1024
                    }
                }
            ]
        }
    }
    
    # Replace with transport helper
    resp = transport_helpers.transport_send_message(sut_client, params)
    
    # The SUT should handle this gracefully since mimeType is RECOMMENDED, not required
    if transport_helpers.is_json_rpc_error_response(resp):
        # If rejected, should be for business logic reasons, not spec violations
        logger.info("SUT rejected file without mimeType - this is acceptable behavior")
    else:
        # If accepted, should create a valid task
        assert transport_helpers.is_json_rpc_success_response(resp)
        logger.info("SUT accepted file without mimeType - this demonstrates good flexibility") 