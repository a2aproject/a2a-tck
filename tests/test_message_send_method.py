import logging
import uuid

import pytest

from tck import agent_card_utils, message_utils
from tck.sut_client import SUTClient

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()

@pytest.fixture
def valid_text_message_params():
    # Minimal valid params for message/send (TextPart)
    return {
        "message": {
            "messageId": "test-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Hello from TCK!"
                }
            ]
        }
    }

@pytest.fixture
def valid_file_message_params():
    # Valid params for message/send with FilePart
    return {
        "message": {
            "messageId": "test-file-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "file",
                    "file": {
                        "name": "test.txt",
                        "mimeType": "text/plain",
                        "url": "https://example.com/test.txt",
                        "sizeInBytes": 1024
                    }
                }
            ]
        }
    }

@pytest.fixture
def valid_data_message_params():
    # Valid params for message/send with DataPart
    return {
        "message": {
            "messageId": "test-data-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "data",
                    "data": {
                        "key": "value",
                        "number": 123,
                        "nested": {
                            "array": [1, 2, 3]
                        }
                    }
                }
            ]
        }
    }

# Helper functions for modality checking
def has_modality_support(agent_card_data, modality):
    """Check if the SUT supports a specific modality based on Agent Card data."""
    if agent_card_data is None:
        logger.warning(f"Agent Card data is None, assuming {modality} modality is supported")
        return True  # Default to assuming support if we can't check
    
    modalities = agent_card_utils.get_supported_modalities(agent_card_data)
    supported = modality in modalities
    
    if not supported:
        logger.info(f"Modality '{modality}' not found in supported modalities: {modalities}")
    
    return supported

@pytest.mark.core
def test_message_send_valid_text(sut_client, valid_text_message_params, agent_card_data):
    """
    A2A JSON-RPC Spec: message/send
    Test sending a valid message with a TextPart. Expect a Task or Message object in result.
    """
    # Text modality is considered fundamental, but check anyway
    if not has_modality_support(agent_card_data, "text"):
        logger.warning("Agent Card does not declare 'text' modality support, but testing anyway as it's fundamental")
    
    req = message_utils.make_json_rpc_request("message/send", params=valid_text_message_params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    result = resp["result"]

    # According to A2A spec, message/send can return either Task or Message
    if "status" in result:
        # This is a Task object
        assert result.get("status", {}).get("state") in {"submitted", "working", "input_required", "completed"}
    else:
        # This is a Message object - verify it has the expected structure
        assert result.get("kind") == "message"
        assert result.get("role") == "agent"
        assert "parts" in result

@pytest.mark.core
def test_message_send_invalid_params(sut_client):
    """
    A2A JSON-RPC Spec: message/send
    Test sending a message with missing required fields. Expect InvalidParamsError (-32602).
    """
    invalid_params = {"message": {}}  # missing parts
    req = message_utils.make_json_rpc_request("message/send", params=invalid_params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    #assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"])
    assert resp["error"]["code"] == -32602

def test_message_send_valid_file_part(sut_client, valid_file_message_params, agent_card_data):
    """
    A2A JSON-RPC Spec: message/send
    Test sending a valid message with a FilePart. Expect a Task object in result.
    """
    # Skip if file modality is not supported
    if not has_modality_support(agent_card_data, "file"):
        pytest.skip("File modality not supported by SUT according to Agent Card")
    
    # Mark as core since we've confirmed file modality is supported
    pytestmark = pytest.mark.core
    
    req = message_utils.make_json_rpc_request("message/send", params=valid_file_message_params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    result = resp["result"]

    assert result.get("status", {}).get("state") in {"submitted", "working", "input_required", "completed"}

def test_message_send_valid_multiple_parts(sut_client, valid_text_message_params, valid_file_message_params, agent_card_data):
    """
    A2A JSON-RPC Spec: message/send
    Test sending a valid message with multiple parts. Expect a Task object in result.
    """
    # Skip if file modality is not supported (we already assume text is supported)
    if not has_modality_support(agent_card_data, "file"):
        pytest.skip("File modality not supported by SUT according to Agent Card")
    
    # Mark as core since we've confirmed support for both modalities
    pytestmark = pytest.mark.core
    
    combined_parts = {
        "message": {
            "messageId": "test-multiple-parts-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": valid_text_message_params["message"]["parts"] + valid_file_message_params["message"]["parts"]
        }
    }
    req = message_utils.make_json_rpc_request("message/send", params=combined_parts)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    result = resp["result"]

    assert result.get("status", {}).get("state") in {"submitted", "working", "input_required", "completed"}

@pytest.mark.core
def test_message_send_continue_task(sut_client, valid_text_message_params):
    """
    A2A JSON-RPC Spec: message/send
    Test continuing an existing task. Expect a Task or Message object in result with the provided taskId.
    """
    # First, create a task with an explicit taskId
    task_id = "test-continue-task-" + str(uuid.uuid4())
    first_params = valid_text_message_params.copy()
    first_params["message"]["taskId"] = task_id
    
    first_req = message_utils.make_json_rpc_request("message/send", params=first_params)
    first_resp = sut_client.send_json_rpc(method=first_req["method"], params=first_req["params"], id=first_req["id"])
    assert message_utils.is_json_rpc_success_response(first_resp, expected_id=first_req["id"])
    
    # Now, send a follow-up message to continue the task
    continuation_params = {
        "message": {
            "taskId": task_id,
            "messageId": "test-continuation-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Follow-up message for the existing task"
                }
            ]
        }
    }
    second_req = message_utils.make_json_rpc_request("message/send", params=continuation_params)
    second_resp = sut_client.send_json_rpc(method=second_req["method"], params=second_req["params"], id=second_req["id"])
    assert message_utils.is_json_rpc_success_response(second_resp, expected_id=second_req["id"])
    result = second_resp["result"]
    
    # The result can be either a Task or Message object
    if "status" in result:
        # This is a Task object
        assert result["id"] == task_id  # Should be the same task ID
        assert result.get("status", {}).get("state") in {"submitted", "working", "input_required", "completed"}
    else:
        # This is a Message object - verify it has the expected structure
        assert result.get("kind") == "message"
        assert result.get("role") == "agent"
        assert "parts" in result

@pytest.mark.core
def test_message_send_continue_nonexistent_task(sut_client):
    """
    A2A JSON-RPC Spec: message/send
    Test continuing a non-existent task. Expect TaskNotFoundError or similar.
    """
    continuation_params = {
        "message": {
            "taskId": "non-existent-task-id",
            "messageId": "test-nonexistent-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Message for a non-existent task"
                }
            ]
        }
    }
    req = message_utils.make_json_rpc_request("message/send", params=continuation_params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"])
    # Error code might be implementation-specific, but should be an error

def test_message_send_continue_with_contextid(sut_client, valid_text_message_params):
    """
    A2A JSON-RPC Spec: message/send with contextId
    Test continuing an existing task with contextId. Expect a Task object with the same taskId.
    """
    # First, create a task
    first_req = message_utils.make_json_rpc_request("message/send", params=valid_text_message_params)
    first_resp = sut_client.send_json_rpc(method=first_req["method"], params=first_req["params"], id=first_req["id"])
    assert message_utils.is_json_rpc_success_response(first_resp, expected_id=first_req["id"])
    task_id = first_resp["result"]["id"]
    
    # Check if the response contains a contextId we can use
    context_id = None
    if "result" in first_resp and isinstance(first_resp["result"], dict):
        context_id = first_resp["result"].get("contextId")
    
    # If no contextId was provided, create a dummy one
    if not context_id:
        context_id = f"tck-context-{message_utils.generate_request_id()}"
        logger.info(f"No contextId found in initial task, using dummy: {context_id}")
    
    # Send a follow-up message with both taskId and contextId
    continuation_params = {
        "message": {
            "taskId": task_id,
            "contextId": context_id,
            "messageId": "test-contextid-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Follow-up message for the existing task with contextId"
                }
            ]
        }
    }
    second_req = message_utils.make_json_rpc_request("message/send", params=continuation_params)
    second_resp = sut_client.send_json_rpc(method=second_req["method"], params=second_req["params"], id=second_req["id"])
    assert message_utils.is_json_rpc_success_response(second_resp, expected_id=second_req["id"])
    result = second_resp["result"]
    assert result["id"] == task_id  # Should be the same task ID
    assert result.get("status", {}).get("state") in {"submitted", "working", "input_required", "completed"}

def test_message_send_valid_data_part(sut_client, valid_data_message_params, agent_card_data):
    """
    A2A JSON-RPC Spec: message/send with DataPart
    Test sending a valid message with a DataPart. Expect a Task object in result.
    """
    # Skip if data modality is not supported
    if not has_modality_support(agent_card_data, "data"):
        pytest.skip("Data modality not supported by SUT according to Agent Card")
    
    req = message_utils.make_json_rpc_request("message/send", params=valid_data_message_params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    result = resp["result"]

    assert result.get("status", {}).get("state") in {"submitted", "working", "input_required", "completed"}

def test_message_send_data_part_array(sut_client, agent_card_data):
    """
    A2A JSON-RPC Spec: message/send with DataPart (array)
    Test sending a DataPart with an array. Expect a Task object in result.
    """
    # Skip if data modality is not supported
    if not has_modality_support(agent_card_data, "data"):
        pytest.skip("Data modality not supported by SUT according to Agent Card")
    
    params = {
        "message": {
            "messageId": "test-array-data-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "data",
                    "data": [1, "string", {"nested": True}]
                }
            ]
        }
    }
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    assert "id" in resp["result"]
