"""
A2A Protocol Specification: Message send capability-dependent tests.

This test suite validates capability-dependent message/send functionality
according to the A2A specification: https://google.github.io/A2A/specification/#message-send
"""

import logging
import uuid

import pytest

from tck import message_utils
from tck.sut_client import SUTClient
from tests.markers import optional_capability
from tests.capability_validator import has_modality_support

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()

@optional_capability
def test_message_send_valid_file_part(sut_client, valid_file_message_params, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §6.6.2 - File Modality Support
    
    Status: MANDATORY if file modality declared in Agent Card
            SKIP if file modality not declared
            
    If an agent declares file modality support, it MUST properly
    handle message/send with FilePart containing FileWithUri objects.
    
    Failure Impact: False advertising if declared but not implemented
    Fix Suggestion: Either implement file support or remove from Agent Card
    
    Asserts:
        - File parts are processed successfully when file modality is declared
        - Task is created in valid state
        - Response follows A2A specification format
    """
    # Skip if file modality is not supported
    if not has_modality_support(agent_card_data, "file"):
        pytest.skip("File modality not supported by SUT according to Agent Card")
    
    req = message_utils.make_json_rpc_request("message/send", params=valid_file_message_params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    result = resp["result"]

    assert result.get("status", {}).get("state") in {"submitted", "working", "input_required", "completed"}

@optional_capability
def test_message_send_valid_multiple_parts(sut_client, valid_text_message_params, valid_file_message_params, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §6.6 - Multiple Parts Support
    
    Status: MANDATORY if multiple modalities declared
            SKIP if file modality not declared
            
    If an agent supports multiple modalities, it MUST handle
    messages with multiple part types.
    
    Failure Impact: False advertising if declared but not implemented
    Fix Suggestion: Either implement multi-modal support or limit Agent Card declarations
    
    Asserts:
        - Multiple part types are processed successfully when modalities are declared
        - Combined text and file parts work together
        - Task is created in valid state
    """
    # Skip if file modality is not supported (we already assume text is supported)
    if not has_modality_support(agent_card_data, "file"):
        pytest.skip("File modality not supported by SUT according to Agent Card")
    
    combined_parts = {
        "message": {
            "kind": "message",
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

@optional_capability
def test_message_send_continue_with_contextid(sut_client, valid_text_message_params):
    """
    OPTIONAL CAPABILITY: A2A Specification §6.5 - Context Management
    
    Tests optional context ID parameter for message continuation.
    Context management allows agents to maintain conversation context
    across multiple task interactions.
    
    Failure Impact: Limits conversation continuity (perfectly acceptable)
    Fix Suggestion: Implement context management for enhanced user experience
    
    Asserts:
        - Context ID parameter is accepted when provided
        - Context is properly maintained across messages
        - Valid JSON-RPC response is returned
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
            "kind": "message",
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

@optional_capability
def test_message_send_valid_data_part(sut_client, valid_data_message_params, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §6.6.3 - Data Modality Support
    
    Status: MANDATORY if data modality declared in Agent Card
            SKIP if data modality not declared
            
    If an agent declares data modality support, it MUST properly
    handle message/send with DataPart.
    
    Failure Impact: False advertising if declared but not implemented
    Fix Suggestion: Either implement data support or remove from Agent Card
    
    Asserts:
        - Data parts are processed successfully when data modality is declared
        - Task is created in valid state
        - Response follows A2A specification format
    """
    # Skip if data modality is not supported
    if not has_modality_support(agent_card_data, "data"):
        pytest.skip("Data modality not supported by SUT according to Agent Card")
    
    req = message_utils.make_json_rpc_request("message/send", params=valid_data_message_params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    result = resp["result"]

    assert result.get("status", {}).get("state") in {"submitted", "working", "input_required", "completed"}

@optional_capability
def test_message_send_data_part_array(sut_client, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §5.1 - Data Array Support
    
    Status: MANDATORY if data modality declared in Agent Card
            SKIP if data modality not declared
            
    If an agent declares data modality support, it MUST properly
    handle message/send with DataPart containing arrays.
    
    Failure Impact: False advertising if declared but not implemented
    Fix Suggestion: Either implement full data support or remove from Agent Card
    
    Asserts:
        - Data parts with arrays are processed when data modality is declared
        - Complex data structures are handled properly
        - Task is created in valid state
    """
    # Skip if data modality is not supported
    if not has_modality_support(agent_card_data, "data"):
        pytest.skip("Data modality not supported by SUT according to Agent Card")
    
    # Create a message with data part containing an array
    data_array_params = {
        "message": {
            "kind": "message",
            "messageId": "test-data-array-message-id-" + str(uuid.uuid4()),
            "role": "user", 
            "parts": [
                {
                    "kind": "data",
                    "data": [
                        {"name": "Alice", "age": 30},
                        {"name": "Bob", "age": 25},
                        {"name": "Charlie", "age": 35}
                    ]
                }
            ]
        }
    }
    
    req = message_utils.make_json_rpc_request("message/send", params=data_array_params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    result = resp["result"]

    assert result.get("status", {}).get("state") in {"submitted", "working", "input_required", "completed"} 
