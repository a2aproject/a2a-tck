import logging
import uuid

import pytest

from tck import agent_card_utils, message_utils
from tests.markers import mandatory_protocol, optional_capability
from tests.utils.transport_helpers import (
    transport_send_message,
    is_json_rpc_success_response,
    extract_task_id_from_response,
    generate_test_message_id,
)

logger = logging.getLogger(__name__)


@pytest.fixture
def valid_text_message_params():
    # Minimal valid params for SendMessage (TextPart)
    # Uses transport-agnostic message ID generation
    return {
        "message": {
            "messageId": generate_test_message_id("text"),
            "role": "ROLE_USER",
            "parts": [{"text": "Hello from TCK!"}],
        }
    }


@pytest.fixture
def valid_file_message_params():
    # Valid params for SendMessage with FilePart
    # Note: mimeType is RECOMMENDED per A2A v1.0 §4.1.7 FilePart
    return {
        "message": {
            "messageId": generate_test_message_id("file"),
            "role": "ROLE_USER",
            "parts": [
                {
                    "file": {
                        "name": "test.txt",
                        "mimeType": "text/plain",
                        "fileWithUri": "https://example.com/test.txt",
                    },
                }
            ],
        }
    }


@pytest.fixture
def valid_data_message_params():
    # Valid params for SendMessage with DataPart
    return {
        "message": {
            "messageId": generate_test_message_id("data"),
            "role": "ROLE_USER",
            "parts": [{"data": {"key": "value", "number": 123, "nested": {"array": [1, 2, 3]}}}],
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
    MANDATORY: A2A v1.0 §9.4.1. SendMessage

    The A2A v1.0 specification requires all implementations to support
    SendMessage with text content as the fundamental communication method.
    This test works across all transport types (JSON-RPC, gRPC, REST).

    Failure Impact: Implementation is not A2A v1.0 compliant

    Specification Reference: A2A v1.0 §9.4.1. SendMessage
    """
    # Text modality is considered fundamental, but check anyway
    if not has_modality_support(agent_card_data, "text"):
        logger.warning("Agent Card does not declare 'text' modality support, but testing anyway as it's fundamental")

    # Use transport-agnostic message sending
    resp = transport_send_message(sut_client, valid_text_message_params)

    # Validate response using transport-agnostic validation
    assert is_json_rpc_success_response(resp), f"Message send failed: {resp}"

    # Extract result from transport response
    result = resp.get("result", resp)

    # According to A2A v1.0 spec, SendMessage can return either Task or Message
    if "task" in result:
        # This is a Task object
        assert result["task"]["status"]["state"] in {"TASK_STATE_SUBMITTED", "TASK_STATE_WORKING", "TASK_STATE_INPUT_REQUIRED", "TASK_STATE_COMPLETED"}
    elif "message" in result:
        assert result["message"]["role"] == "ROLE_AGENT"
        assert "parts" in result["message"]
    else:
        assert False, f"Unknown result to SendMessage: {result}"


@mandatory_protocol
def test_message_send_invalid_params(sut_client):
    """
    MANDATORY: A2A v1.0 §9.5. Error Handling

    The A2A v1.0 specification requires proper validation of message/send parameters.
    Missing required fields MUST result in InvalidParamsError (-32602).
    This test works across all transport types.

    Failure Impact: Implementation is not A2A v1.0 compliant

    Specification Reference: A2A v1.0 §9.5. Error Handling
    """
    #FIXME a2a-java with {"message": {"messageId": "123"}}, it raises {'code': -32603, 'message': "Parameter 'role' may not be null"}
    invalid_params = {"message": {"kind": "message"}}  # missing required fields (messageId, role, parts)

    # Use transport-agnostic message sending (should fail)
    resp = transport_send_message(sut_client, invalid_params)

    # Check for proper error response across transports
    assert "error" in resp or not is_json_rpc_success_response(resp), "Invalid parameters should result in error response"

    logger.info(f"Invalid params response: {resp}")
    # For JSON-RPC, verify specific error code
    if "error" in resp and "code" in resp["error"]:
        assert resp["error"]["code"] == -32602, f"Expected InvalidParamsError (-32602), got {resp['error']['code']}"


@mandatory_protocol
def test_message_send_continue_task(sut_client, valid_text_message_params):
    """
    MANDATORY: A2A v1.0 FIXME

    The A2A v1.0 specification requires support for continuing existing tasks
    via SendMessage with a Message with the taskId parameter. This test works across all transport types.

    Failure Impact: Implementation is not A2A v1.0 compliant

    Specification Reference: A2A v1.0 FIXME
    """
    # First, create a task using transport-agnostic sending
    first_params = valid_text_message_params.copy()

    first_resp = transport_send_message(sut_client, first_params)
    assert is_json_rpc_success_response(first_resp), f"Initial message send failed: {first_resp}"

    # Extract task ID from transport response
    task_id = extract_task_id_from_response(first_resp)
    assert task_id is not None, "Failed to extract task ID from response"

    # Now, send a follow-up message to continue the task
    continuation_params = {
        "message": {
            "taskId": task_id,
            "messageId": generate_test_message_id("continuation"),
            "role": "ROLE_USER",
            "parts": [{"text": "Follow-up message for the existing task"}],
        }
    }

    second_resp = transport_send_message(sut_client, continuation_params)
    assert is_json_rpc_success_response(second_resp), f"Task continuation failed: {second_resp}"

    # Extract result from transport response
    result = second_resp.get("result", second_resp)

    # According to A2A v1.0 spec, SendMessage can return either Task or Message
    if "task" in result:
        # This is a Task object
        assert result["task"]["id"] == task_id, f"Task ID mismatch: expected {task_id}, got {result['task']['id']}"
        assert result["task"]["status"]["state"] in {"TASK_STATE_SUBMITTED", "TASK_STATE_WORKING", "TASK_STATE_INPUT_REQUIRED", "TASK_STATE_COMPLETED"}
    elif "message" in result:
        assert result["message"]["role"] == "ROLE_AGENT"
        assert "parts" in result["message"]
    else:
        assert False, f"Unknown result to SendMessage: {result}"