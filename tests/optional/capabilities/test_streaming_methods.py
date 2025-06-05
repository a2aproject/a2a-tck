import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional
import uuid

import httpx
import pytest
import pytest_asyncio

from tck import agent_card_utils, config, message_utils
from tck.sut_client import SUTClient
from tests.markers import optional_capability
from tests.capability_validator import CapabilityValidator, skip_if_capability_not_declared

logger = logging.getLogger(__name__)

# SimpleSSEClient to handle Server-Sent Events
class SimpleSSEClient:
    def __init__(self, response: httpx.Response):
        self.response = response
        self.buffer = ""
        
    async def __aiter__(self):
        async for line in self.response.aiter_lines():
            self.buffer += line + "\n"
            if self.buffer.endswith("\n\n"):
                event_data = self._parse_event(self.buffer.strip())
                self.buffer = ""
                if event_data:
                    yield event_data
        
        # Handle any remaining data in buffer
        if self.buffer:
            event_data = self._parse_event(self.buffer.strip())
            if event_data:
                yield event_data
    
    def _parse_event(self, buffer: str) -> Optional[Dict[str, str]]:
        """Parse SSE event from buffer."""
        if not buffer:
            return None
            
        event = {}
        for line in buffer.split('\n'):
            if not line:
                continue
                
            if ':' in line:
                field, value = line.split(':', 1)
                if value.startswith(' '):
                    value = value[1:]
                event[field] = value
        
        return event if event else None

@pytest_asyncio.fixture
async def async_http_client():
    """Fixture for async HTTP client."""
    async with httpx.AsyncClient() as client:
        yield client

# Helper function to check streaming support from Agent Card
def has_streaming_support(agent_card_data) -> bool:
    """Check if the SUT supports streaming based on Agent Card data."""
    if agent_card_data is None:
        logger.warning("Agent Card data is None, assuming streaming is not supported")
        return False
    
    return agent_card_utils.get_capability_streaming(agent_card_data)

@optional_capability
@pytest.mark.asyncio
async def test_message_stream_basic(async_http_client, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §8.1 - Streaming Support
    
    Status: MANDATORY if capabilities.streaming = true
            SKIP if capabilities.streaming = false/missing
            
    The A2A specification states that IF an agent declares
    streaming capability, it MUST implement message/stream correctly.
    
    Test validates:
    - HTTP 200 response with Content-Type: text/event-stream
    - Proper SSE event format
    - Valid JSON-RPC responses in events
    - Proper task/message data structures
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('streaming'):
        pytest.skip("Streaming capability not declared - test not applicable")
        
    # If we get here, streaming is declared so test MUST pass
    # This is now a MANDATORY test because capability was declared
    
    # Prepare the streaming request payload
    params = {
        "message": {
            "kind": "message",
            "messageId": "test-stream-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Stream test message"
                }
            ]
        }
    }
    
    req_id = message_utils.generate_request_id()
    json_rpc_request = message_utils.make_json_rpc_request("message/stream", params=params, id=req_id)
    
    # Send the request and expect a streaming response
    sut_url = config.get_sut_url()
    headers = {"Content-Type": "application/json"}
    
    try:
        response = await async_http_client.post(
            sut_url,
            json=json_rpc_request,
            headers=headers,
            timeout=None  # No timeout for streaming
        )
        
        assert response.status_code == 200, "Streaming capability declared but HTTP 200 not returned"
        assert response.headers.get("content-type", "").startswith("text/event-stream"), \
            "Streaming capability declared but Content-Type is not text/event-stream"
        
        # Process the SSE stream
        sse_client = SimpleSSEClient(response)
        events = []
        
        # Collect events with a timeout to avoid hanging indefinitely
        try:
            async for event in sse_client:
                if "data" in event:
                    try:
                        data = json.loads(event["data"])
                        events.append(data)
                        logger.info(f"Received SSE event: {data}")
                        
                        # Check if this is a terminal event to break the loop
                        if "result" in data and isinstance(data["result"], dict):
                            status = data["result"].get("status", {})
                            if isinstance(status, dict) and status.get("state") in ["completed", "failed", "canceled"]:
                                logger.info("Detected terminal event, ending stream processing.")
                                break
                                
                        # Break after a reasonable number of events for testing
                        if len(events) >= 5:
                            logger.info("Collected 5 events, ending stream processing.")
                            break
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse event data as JSON: {event['data']}")
                        continue
        except asyncio.TimeoutError:
            logger.warning("Timeout while processing SSE stream")
        
        # Validate the collected events
        assert len(events) > 0, "Streaming capability declared but no events received from stream"
        
        # Check that the received events match our expectations
        for event in events:
            assert message_utils.is_json_rpc_success_response(event, expected_id=req_id) or \
                   message_utils.is_json_rpc_error_response(event, expected_id=req_id), \
                   "Streaming capability declared but invalid JSON-RPC responses received"
            
            if message_utils.is_json_rpc_success_response(event, expected_id=req_id):
                # The result should be a Task, Message, TaskStatusUpdateEvent, or TaskArtifactUpdateEvent
                result = event["result"]
                assert isinstance(result, dict), "Streaming result must be an object"
                
                # Event type should be identifiable (this would be better with proper schema validation)
                if "status" in result and "id" in result:
                    # Looks like a Task
                    assert isinstance(result["status"], dict)
                elif "kind" in result and result.get("kind") == "status-update":
                    # Looks like a TaskStatusUpdateEvent
                    assert "taskId" in result
                elif "kind" in result and result.get("kind") == "artifact-update":
                    # Looks like a TaskArtifactUpdateEvent
                    assert "taskId" in result
                    assert "artifact" in result
                # Otherwise it might be a Message or other valid type
                
    except httpx.HTTPError as e:
        if hasattr(e, "response") and e.response.status_code == 501:
            # This is a FAILURE because streaming was declared but not implemented
            pytest.fail(
                "Streaming capability declared in Agent Card but SUT returned HTTP 501 Not Implemented. "
                "This is a specification violation - declared capabilities MUST be implemented."
            )
        else:
            raise

@optional_capability
@pytest.mark.asyncio
async def test_message_stream_invalid_params(async_http_client, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §8.1 - Streaming Parameter Validation
    
    Status: MANDATORY if capabilities.streaming = true
            SKIP if capabilities.streaming = false/missing
            
    Test validates that streaming endpoints properly validate parameters
    and return appropriate JSON-RPC error responses for invalid input.
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('streaming'):
        pytest.skip("Streaming capability not declared - test not applicable")

    # Test with invalid params structure
    req_id = message_utils.generate_request_id()
    json_rpc_request = message_utils.make_json_rpc_request(
        "message/stream",
        params={"invalid": "params"}, 
        id=req_id
    )
    
    sut_url = config.get_sut_url()
    headers = {"Content-Type": "application/json"}
    
    response = await async_http_client.post(
        sut_url,
        json=json_rpc_request,
        headers=headers
    )
    
    # Should return JSON-RPC error, not streaming response
    assert response.status_code == 200, "Should return JSON-RPC error response, not HTTP error"
    assert response.headers.get("content-type", "").startswith("application/json"), \
        "Invalid params should return JSON-RPC error, not SSE stream"
    
    response_data = response.json()
    assert message_utils.is_json_rpc_error_response(response_data, expected_id=req_id), \
        "Streaming capability declared but invalid params not properly rejected"

@optional_capability
@pytest.mark.asyncio
async def test_tasks_resubscribe(async_http_client, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §8.2 - Task Resubscription
    
    Status: MANDATORY if capabilities.streaming = true
            SKIP if capabilities.streaming = false/missing
            
    Test validates the tasks/resubscribe method for existing tasks.
    This method allows clients to resubscribe to SSE streams for ongoing tasks.
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('streaming'):
        pytest.skip("Streaming capability not declared - test not applicable")
    
    # First, create a task via message/send
    sut_client = SUTClient()
    message_params = {
        "message": {
            "kind": "message",
            "messageId": "test-resubscribe-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Test message for resubscribe"
                }
            ]
        }
    }
    
    send_response = sut_client.send_json_rpc("message/send", params=message_params)
    assert message_utils.is_json_rpc_success_response(send_response)
    
    # Extract the task ID from the response
    task = send_response["result"]
    assert isinstance(task, dict)
    assert "id" in task
    task_id = task["id"]
    
    # Now try to resubscribe to this task
    resubscribe_params = {"id": task_id}
    req_id = message_utils.generate_request_id()
    json_rpc_request = message_utils.make_json_rpc_request("tasks/resubscribe", params=resubscribe_params, id=req_id)
    
    sut_url = config.get_sut_url()
    headers = {"Content-Type": "application/json"}
    
    try:
        response = await async_http_client.post(
            sut_url,
            json=json_rpc_request,
            headers=headers,
            timeout=None
        )
        
        assert response.status_code == 200, "Streaming capability declared but resubscribe failed"
        assert response.headers.get("content-type", "").startswith("text/event-stream"), \
            "Streaming capability declared but resubscribe didn't return SSE stream"
        
        # Process the SSE stream similar to message/stream test
        sse_client = SimpleSSEClient(response)
        events = []
        
        try:
            async for event in sse_client:
                if "data" in event:
                    try:
                        data = json.loads(event["data"])
                        events.append(data)
                        logger.info(f"Received resubscribe SSE event: {data}")
                        
                        # Check if this is a terminal event
                        if "result" in data and isinstance(data["result"], dict):
                            status = data["result"].get("status", {})
                            if isinstance(status, dict) and status.get("state") in ["completed", "failed", "canceled"]:
                                logger.info("Detected terminal event in resubscribe, ending stream processing.")
                                break
                                
                        # Collect a few events then break
                        if len(events) >= 3:
                            break
                            
                    except json.JSONDecodeError:
                        continue
        except asyncio.TimeoutError:
            logger.warning("Timeout while processing resubscribe SSE stream")
        
        # Validate that we got at least some events
        assert len(events) > 0, "Streaming capability declared but no events received from resubscribe stream"
        
    except httpx.HTTPError as e:
        if hasattr(e, "response") and e.response.status_code == 501:
            pytest.fail(
                "Streaming capability declared but tasks/resubscribe returned HTTP 501. "
                "This violates the A2A specification - declared capabilities MUST be implemented."
            )
        else:
            raise

@optional_capability
@pytest.mark.asyncio
async def test_tasks_resubscribe_nonexistent(async_http_client, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §8.2 - Resubscribe Error Handling
    
    Status: MANDATORY if capabilities.streaming = true
            SKIP if capabilities.streaming = false/missing
            
    Test validates that tasks/resubscribe properly handles non-existent task IDs
    with appropriate JSON-RPC error responses.
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('streaming'):
        pytest.skip("Streaming capability not declared - test not applicable")
    
    # Use a random, non-existent task ID
    task_id = "non-existent-task-id-" + message_utils.generate_request_id()
    
    resubscribe_params = {"id": task_id}
    req_id = message_utils.generate_request_id()
    json_rpc_request = message_utils.make_json_rpc_request("tasks/resubscribe", params=resubscribe_params, id=req_id)
    
    sut_url = config.get_sut_url()
    headers = {"Content-Type": "application/json"}
    
    try:
        response = await async_http_client.post(
            sut_url,
            json=json_rpc_request,
            headers=headers,
            timeout=10  # Use timeout here since we expect an error
        )
        
        # We expect a JSON-RPC error for a non-existent task, not a stream
        assert not response.headers.get("content-type", "").startswith("text/event-stream"), \
            "Non-existent task should return JSON-RPC error, not SSE stream"
        assert response.status_code == 200, "JSON-RPC errors should use HTTP 200"
        
        # Parse and validate the error
        json_response = response.json()
        assert message_utils.is_json_rpc_error_response(json_response, expected_id=req_id), \
            "Streaming capability declared but invalid task ID not properly rejected"
        
        # Error code should indicate task not found
        error = json_response["error"]
        assert "code" in error
        
        # Check the error message to see if it indicates the task wasn't found
        assert "message" in error
        error_message = error["message"].lower()
        assert "not found" in error_message or "task" in error_message, \
            "Error message should clearly indicate task was not found"
        
    except httpx.HTTPError as e:
        if hasattr(e, "response") and e.response.status_code == 501:
            pytest.fail(
                "Streaming capability declared but tasks/resubscribe returned HTTP 501. "
                "This violates the A2A specification - declared capabilities MUST be implemented."
            )
        else:
            raise
