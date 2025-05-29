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

# Dynamic pytest.mark helper functions
def skip_if_streaming_not_supported(agent_card_data):
    """Return a skipif marker if streaming is not supported."""
    return pytest.mark.skipif(
        not has_streaming_support(agent_card_data),
        reason="Streaming not supported by SUT according to Agent Card"
    )

@pytest.mark.asyncio
async def test_message_stream_basic(async_http_client, agent_card_data):
    """
    A2A JSON-RPC Spec: message/stream
    Test the SUT's ability to stream responses using Server-Sent Events (SSE).
    Expect HTTP 200 and Content-Type: text/event-stream.
    """
    # Skip if streaming is not supported
    if not has_streaming_support(agent_card_data):
        pytest.skip("Streaming not supported by SUT according to Agent Card")
    
    # Mark as core since we've confirmed streaming is supported
    pytestmark = pytest.mark.core
    
    # Prepare the streaming request payload
    params = {
        "message": {
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
        
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/event-stream")
        
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
        assert len(events) > 0, "No events received from the stream"
        
        # Check that the received events match our expectations
        for event in events:
            assert message_utils.is_json_rpc_success_response(event, expected_id=req_id) or \
                   message_utils.is_json_rpc_error_response(event, expected_id=req_id)
            
            if message_utils.is_json_rpc_success_response(event, expected_id=req_id):
                # The result should be a Task, Message, TaskStatusUpdateEvent, or TaskArtifactUpdateEvent
                result = event["result"]
                assert isinstance(result, dict)
                
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
            # Not Implemented - if streaming is not supported, this is acceptable
            pytest.skip("Streaming not supported by SUT (HTTP 501)")
        else:
            raise

@pytest.mark.asyncio
async def test_message_stream_invalid_params(async_http_client, agent_card_data):
    """
    A2A JSON-RPC Spec: message/stream
    Test sending a message/stream request with invalid params.
    Expect either an immediate JSON-RPC error or an error in the stream.
    """
    # Skip if streaming is not supported
    if not has_streaming_support(agent_card_data):
        pytest.skip("Streaming not supported by SUT according to Agent Card")
    
    # Mark as core since we've confirmed streaming is supported
    pytestmark = pytest.mark.core
    
    # Invalid params: missing required parts field
    params = {"message": {}}
    
    req_id = message_utils.generate_request_id()
    json_rpc_request = message_utils.make_json_rpc_request("message/stream", params=params, id=req_id)
    
    sut_url = config.get_sut_url()
    headers = {"Content-Type": "application/json"}
    
    try:
        response = await async_http_client.post(
            sut_url,
            json=json_rpc_request,
            headers=headers,
            timeout=30  # Use timeout here because we expect an error
        )
        
        # If we get a non-streaming response, it should be a JSON-RPC error
        if not response.headers.get("content-type", "").startswith("text/event-stream"):
            assert response.status_code == 200  # JSON-RPC errors still return HTTP 200
            
            # Parse the response and validate it's a proper JSON-RPC error
            try:
                json_response = response.json()
                assert message_utils.is_json_rpc_error_response(json_response, expected_id=req_id)
                # Should have InvalidParams code or similar
                assert "error" in json_response
                assert "code" in json_response["error"]
                assert json_response["error"]["code"] in [-32602, -32600]  # Invalid params or invalid request
            except json.JSONDecodeError:
                pytest.fail("Non-streaming response was not valid JSON")
            except AssertionError as e:
                pytest.fail(f"Response was not a valid JSON-RPC error: {e}")
                
        # If we get a streaming response despite invalid params, check for an error event
        else:
            sse_client = SimpleSSEClient(response)
            got_error = False
            
            # Process a few events, looking for an error
            try:
                async for event in sse_client:
                    if "data" in event:
                        try:
                            data = json.loads(event["data"])
                            logger.info(f"Received SSE event for invalid params: {data}")
                            
                            # If we get an error response, that's acceptable
                            if message_utils.is_json_rpc_error_response(data, expected_id=req_id):
                                got_error = True
                                break
                                
                        except json.JSONDecodeError:
                            continue
            except asyncio.TimeoutError:
                logger.warning("Timeout while processing SSE stream")
            
            # We should have received an error somewhere in the stream
            assert got_error, "Expected an error response for invalid params in the SSE stream"
        
    except httpx.HTTPError as e:
        if hasattr(e, "response") and e.response.status_code == 501:
            pytest.skip("Streaming not supported by SUT (HTTP 501)")
        else:
            raise

@pytest.mark.asyncio
async def test_tasks_resubscribe(async_http_client, agent_card_data):
    """
    A2A JSON-RPC Spec: tasks/resubscribe
    Test the SUT's ability to handle resubscribing to an existing task's SSE stream.
    """
    # Skip if streaming is not supported
    if not has_streaming_support(agent_card_data):
        pytest.skip("Streaming not supported by SUT according to Agent Card")
    
    # Mark as core since we've confirmed streaming is supported
    pytestmark = pytest.mark.core
    
    # First, create a task via message/send
    sut_client = SUTClient()
    message_params = {
        "message": {
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
        
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/event-stream")
        
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
        assert len(events) > 0, "No events received from resubscribe stream"
        
    except httpx.HTTPError as e:
        if hasattr(e, "response") and e.response.status_code == 501:
            pytest.skip("Streaming or resubscribe not supported by SUT (HTTP 501)")
        else:
            raise

@pytest.mark.asyncio
async def test_tasks_resubscribe_nonexistent(async_http_client, agent_card_data):
    """
    A2A JSON-RPC Spec: tasks/resubscribe for non-existent task
    Test the SUT's handling of a resubscribe request for a task that doesn't exist.
    Expect a JSON-RPC error with TaskNotFoundError or similar.
    """
    # Skip if streaming is not supported
    if not has_streaming_support(agent_card_data):
        pytest.skip("Streaming not supported by SUT according to Agent Card")
    
    # Mark as core since we've confirmed streaming is supported
    pytestmark = pytest.mark.core
    
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
        assert not response.headers.get("content-type", "").startswith("text/event-stream")
        assert response.status_code == 200  # JSON-RPC errors still use HTTP 200
        
        # Parse and validate the error
        json_response = response.json()
        assert message_utils.is_json_rpc_error_response(json_response, expected_id=req_id)
        
        # Error code should indicate task not found
        # The exact code depends on the SUT's convention, but often follows the pattern of json-rpc error codes
        error = json_response["error"]
        assert "code" in error
        
        # Check the error message to see if it indicates the task wasn't found
        assert "message" in error
        error_message = error["message"].lower()
        assert "not found" in error_message or "task" in error_message
        
    except httpx.HTTPError as e:
        if hasattr(e, "response") and e.response.status_code == 501:
            pytest.skip("Streaming or resubscribe not supported by SUT (HTTP 501)")
        else:
            raise
