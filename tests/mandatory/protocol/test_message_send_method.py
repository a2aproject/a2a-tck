import logging
import uuid

import pytest

from tck import agent_card_utils, message_utils
from tck.sut_client import SUTClient
from tests.markers import mandatory_protocol, optional_capability

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()

@pytest.fixture
def valid_text_message_params():
    # Minimal valid params for message/send (TextPart)
    return {
        "message": {
            "kind": "message",
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
    # Note: mimeType is RECOMMENDED per A2A Specification §6.6.2 FileWithUri Object
    return {
        "message": {
            "kind": "message",
            "messageId": "test-file-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "file",
                    "file": {
                        "name": "test.txt",
                        "mimeType": "text/plain",  # RECOMMENDED: Media Type per A2A Spec §6.6.2
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
            "kind": "message",
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

@mandatory_protocol
def test_message_send_valid_text(sut_client, valid_text_message_params, agent_card_data):
    """
    MANDATORY: A2A Specification §5.1 - Core Message Protocol
    
    The A2A specification requires all implementations to support
    message/send with text content as the fundamental communication method.
    
    Failure Impact: Implementation is not A2A compliant
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

@mandatory_protocol
def test_message_send_invalid_params(sut_client):
    """
    MANDATORY: A2A Specification §5.1 - Parameter Validation
    
    The A2A specification requires proper validation of message/send parameters.
    Missing required fields MUST result in InvalidParamsError (-32602).
    
    Failure Impact: Implementation is not A2A compliant
    """
    invalid_params = {"message": {"kind": "message"}}  # missing required fields (messageId, role, parts)
    req = message_utils.make_json_rpc_request("message/send", params=invalid_params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert resp["error"]["code"] == -32602  # Spec: InvalidParamsError

@mandatory_protocol
def test_message_send_continue_task(sut_client, valid_text_message_params):
    """
    MANDATORY: A2A Specification §5.1 - Task Continuation
    
    The A2A specification requires support for continuing existing tasks
    via message/send with taskId parameter.
    
    Failure Impact: Implementation is not A2A compliant
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
            "kind": "message",
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

