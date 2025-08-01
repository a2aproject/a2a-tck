import asyncio
import json
import logging
import os
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

# Configurable timeout system
# Base timeout can be configured via environment variable TCK_STREAMING_TIMEOUT
# Usage: TCK_STREAMING_TIMEOUT=5.0 python -m pytest ...
# Default is 2.0 seconds if not specified
BASE_TIMEOUT = float(os.getenv('TCK_STREAMING_TIMEOUT', '2.0'))

# Timeout multipliers for different operations
TIMEOUTS = {
    'sse_client_short': BASE_TIMEOUT * 0.5,      # 1.0s default (for basic streaming)
    'sse_client_normal': BASE_TIMEOUT * 1.0,     # 2.0s default (for normal streaming)
    'async_wait_for': BASE_TIMEOUT * 1.0,        # 2.0s default (for asyncio.wait_for)
}

# SimpleSSEClient to handle Server-Sent Events
class SimpleSSEClient:
    def __init__(self, response: httpx.Response, timeout: float = 2.0):
        self.response = response
        self.buffer = ""
        self.timeout = timeout
        
    async def __aiter__(self):
        try:
            async for line in self.response.aiter_lines():
                self.buffer += line + "\n"
                
                # Check for complete event (ends with double newline)
                if self.buffer.endswith("\n\n"):
                    event_data = self._parse_event(self.buffer.strip())
                    self.buffer = ""
                    if event_data:
                        yield event_data
                # Also check for single data line (common SSE format)
                elif line.startswith("data:") and self.buffer.count("\n") >= 2:
                    # We have a data line followed by empty line
                    event_data = self._parse_event(self.buffer.strip())
                    self.buffer = ""
                    if event_data:
                        yield event_data
        except Exception as e:
            logger.error(f"Error in SSE client iteration: {e}")
            # Handle any remaining data in buffer
            if self.buffer:
                event_data = self._parse_event(self.buffer.strip())
                if event_data:
                    yield event_data
            raise
        
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
        async with async_http_client.stream(
            "POST",
            sut_url,
            json=json_rpc_request,
            headers=headers,
        ) as response:
            
            assert response.status_code == 200, "Streaming capability declared but HTTP 200 not returned"
            assert response.headers.get("content-type", "").startswith("text/event-stream"), \
                "Streaming capability declared but Content-Type is not text/event-stream"
            
            # Process the SSE stream
            sse_client = SimpleSSEClient(response, timeout=TIMEOUTS['sse_client_short'])
            events = []
            
            # Collect events with a timeout to avoid hanging indefinitely
            try:
                event_count = 0
                async for event in sse_client:
                    event_count += 1
                    logger.info(f"Processing SSE event #{event_count}: {event}")
                    
                    # Safety break to prevent infinite loops
                    if event_count >= 10:
                        logger.warning("Hit event count limit in basic test, breaking")
                        break
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
async def test_tasks_resubscribe(async_http_client : httpx.AsyncClient, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.9 - Task Resubscription
    
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
    req_id = message_utils.generate_request_id()
    json_rpc_request = message_utils.make_json_rpc_request("message/stream", params=message_params, id=req_id)
    task_id = None  # Initialize task_id outside the loop
     

    # Send the request and expect a streaming response
    sut_url = config.get_sut_url()
    headers = {"Content-Type": "application/json"}
    logger.info(f"Request: {json_rpc_request}")
    try:
        async with async_http_client.stream(
            "POST",
            sut_url,
            json=json_rpc_request,
            headers=headers,
        ) as response:
            logger.info(f"Response: {response}")
            
            assert response.status_code == 200, "Streaming capability declared but HTTP 200 not returned"
            assert response.headers.get("content-type", "").startswith("text/event-stream"), \
                "Streaming capability declared but Content-Type is not text/event-stream"
            # Process the SSE stream
            sse_client = SimpleSSEClient(response, timeout=TIMEOUTS['sse_client_normal'])
            events = []
            
            # Collect events with a timeout to avoid hanging indefinitely
            try:
                async def process_sse_events():
                    event_count = 0
                    async for event in sse_client:
                        event_count += 1
                        logger.info(f"Processing SSE event #{event_count}: {event}")
                        
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
                                if len(events) >= 1:
                                    logger.info("Collected 1 event, ending stream processing.")
                                    break
                            except json.JSONDecodeError:
                                logger.error(f"Failed to parse event data as JSON: {event['data']}")
                                continue
                        
                        # Safety break to prevent infinite loops
                        if event_count >= 10:
                            logger.warning("Hit event count limit, breaking")
                            break
                
                # Add timeout wrapper to prevent indefinite blocking
                await asyncio.wait_for(process_sse_events(), timeout=TIMEOUTS['async_wait_for'])
                
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
                        task_id = result["id"]
                        assert task_id is not None
                        assert task_id != ""
                        assert task_id != "null"
                        assert task_id != "undefined"
                    
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



    
    # Now try to resubscribe to this task
    resubscribe_params = {"id": task_id}
    req_id = message_utils.generate_request_id()
    json_rpc_request = message_utils.make_json_rpc_request("tasks/resubscribe", params=resubscribe_params, id=req_id)
    
    sut_url = config.get_sut_url()
    headers = {"Content-Type": "application/json"}
    
    try:
        async with async_http_client.stream(
            "POST",
            sut_url,
            json=json_rpc_request,
            headers=headers,
        ) as response:
            
            assert response.status_code == 200, "Streaming capability declared but resubscribe failed"
            assert response.headers.get("content-type", "").startswith("text/event-stream"), \
                "Streaming capability declared but resubscribe didn't return SSE stream"
            
            # Process the SSE stream similar to message/stream test
            sse_client = SimpleSSEClient(response, timeout=TIMEOUTS['sse_client_normal'])
            events = []
            
            try:
                async def process_resubscribe_events():
                    event_count = 0
                    async for event in sse_client:
                        event_count += 1
                        logger.info(f"Processing resubscribe SSE event #{event_count}: {event}")
                        
                        # Safety break to prevent infinite loops
                        if event_count >= 10:
                            logger.warning("Hit event count limit in resubscribe test, breaking")
                            break
                        
                        if "data" in event:
                            try:
                                data = json.loads(event["data"])
                                events.append(data)
                                logger.info(f"Received resubscribe SSE event: {data}")
                                # Note: Fixed assertion - should check data, not event
                                assert message_utils.is_json_rpc_success_response(data, expected_id=req_id), "Received an error or unexpected JSON-RPC response in the resubscribe stream"
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
                
                # Add timeout wrapper to prevent indefinite blocking
                await asyncio.wait_for(process_resubscribe_events(), timeout=TIMEOUTS['async_wait_for'])
                
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
    CONDITIONAL MANDATORY: A2A Specification §7.9 - Resubscribe Error Handling
    
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
        async with async_http_client.stream(
            "POST",
            sut_url,
            json=json_rpc_request,
            headers=headers,
        ) as response:
            
            # We expect a stream
            assert response.status_code == 200, "JSON-RPC errors should use HTTP 200"
            assert response.headers.get("content-type", "").startswith("text/event-stream"), \
                "Streaming capability declared but Content-Type is not text/event-stream"

            # Process the SSE stream
            sse_client = SimpleSSEClient(response, timeout=TIMEOUTS['sse_client_normal'])
            events = []
            error = {}

            # Collect events with a timeout to avoid hanging indefinitely
            try:
                event_count = 0
                async for event in sse_client:
                    event_count += 1
                    logger.info(f"Processing nonexistent task SSE event #{event_count}: {event}")
                    
                    # Safety break to prevent infinite loops
                    if event_count >= 10:
                        logger.warning("Hit event count limit in nonexistent task test, breaking")
                        break
                    
                    if "data" in event:
                        try:
                            data = json.loads(event["data"])
                            events.append(data)
                            logger.info(f"Received SSE event: {data}")

                            if "error" in data and isinstance(data["error"], dict):
                                # Error code should indicate task not found
                                error = data["error"]
                                if error:
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
            assert len(events) == 1, "Streaming capability declared but no events received from stream"
            assert error

            # Error code should indicate task not found
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
