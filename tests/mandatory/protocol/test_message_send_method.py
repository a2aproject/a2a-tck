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
    # Minimal valid params for message/send (TextPart)
    # Uses transport-agnostic message ID generation
    return {
        "message": {
            "kind": "message",
            "messageId": generate_test_message_id("text"),
            "role": "user",
            "parts": [{"kind": "text", "text": "Hello from TCK!"}],
        }
    }


@pytest.fixture
def valid_file_message_params():
    # Valid params for message/send with FilePart
    # Note: mimeType is RECOMMENDED per A2A Specification §6.6.2 FileWithUri Object
    return {
        "message": {
            "kind": "message",
            "messageId": generate_test_message_id("file"),
            "role": "user",
            "parts": [
                {
                    "kind": "file",
                    "file": {
                        "name": "test.txt",
                        "mimeType": "text/plain",  # RECOMMENDED: Media Type per A2A Spec §6.6.2
                        "url": "https://example.com/test.txt",
                        "sizeInBytes": 1024,
                    },
                }
            ],
        }
    }


@pytest.fixture
def valid_data_message_params():
    # Valid params for message/send with DataPart
    return {
        "message": {
            "kind": "message",
            "messageId": generate_test_message_id("data"),
            "role": "user",
            "parts": [{"kind": "data", "data": {"key": "value", "number": 123, "nested": {"array": [1, 2, 3]}}}],
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
    MANDATORY: A2A v0.3.0 §7.1 - Core Message Protocol

    The A2A v0.3.0 specification requires all implementations to support
    message/send with text content as the fundamental communication method.
    This test works across all transport types (JSON-RPC, gRPC, REST).

    Failure Impact: Implementation is not A2A v0.3.0 compliant

    Specification Reference: A2A v0.3.0 §7.1 - Core Message Protocol
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

    # According to A2A v0.3.0 spec, message/send can return either Task or Message
    if "status" in result:
        # This is a Task object
        assert result.get("status", {}).get("state") in {"submitted", "working", "input-required", "completed"}
    else:
        # This is a Message object - verify it has the expected structure
        assert result.get("kind") == "message"
        assert result.get("role") == "agent"
        assert "parts" in result


@mandatory_protocol
def test_message_send_invalid_params(sut_client):
    """
    MANDATORY: A2A v0.3.0 §7.1 - Parameter Validation

    The A2A v0.3.0 specification requires proper validation of message/send parameters.
    Missing required fields MUST result in InvalidParamsError (-32602).
    This test works across all transport types.

    Failure Impact: Implementation is not A2A v0.3.0 compliant

    Specification Reference: A2A v0.3.0 §8.1 - Standard JSON-RPC Errors
    """
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
    MANDATORY: A2A v0.3.0 §7.1 - Task Continuation

    The A2A v0.3.0 specification requires support for continuing existing tasks
    via message/send with taskId parameter. This test works across all transport types.

    Failure Impact: Implementation is not A2A v0.3.0 compliant

    Specification Reference: A2A v0.3.0 §7.1 - Core Message Protocol
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
            "kind": "message",
            "taskId": task_id,
            "messageId": generate_test_message_id("continuation"),
            "role": "user",
            "parts": [{"kind": "text", "text": "Follow-up message for the existing task"}],
        }
    }

    second_resp = transport_send_message(sut_client, continuation_params)
    assert is_json_rpc_success_response(second_resp), f"Task continuation failed: {second_resp}"

    # Extract result from transport response
    result = second_resp.get("result", second_resp)

    # The result can be either a Task or Message object
    if "status" in result:
        # This is a Task object
        assert result["id"] == task_id, f"Task ID mismatch: expected {task_id}, got {result.get('id')}"
        assert result.get("status", {}).get("state") in {"submitted", "working", "input-required", "completed"}
    else:
        # This is a Message object - verify it has the expected structure
        assert result.get("kind") == "message"
        assert result.get("role") == "agent"
        assert "parts" in result
