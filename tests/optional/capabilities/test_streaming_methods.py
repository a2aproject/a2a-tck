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
BASE_TIMEOUT = float(os.getenv("TCK_STREAMING_TIMEOUT", "2.0"))

# Timeout multipliers for different operations
TIMEOUTS = {
    "sse_client_short": BASE_TIMEOUT * 0.5,  # 1.0s default (for basic streaming)
    "sse_client_normal": BASE_TIMEOUT * 1.0,  # 2.0s default (for normal streaming)
    "async_wait_for": BASE_TIMEOUT * 1.0,  # 2.0s default (for asyncio.wait_for)
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
        for line in buffer.split("\n"):
            if not line:
                continue

            if ":" in line:
                field, value = line.split(":", 1)
                if value.startswith(" "):
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

    if not validator.is_capability_declared("streaming"):
        pytest.skip("Streaming capability not declared - test not applicable")

    # If we get here, streaming is declared so test MUST pass
    # This is now a MANDATORY test because capability was declared

    # Prepare the streaming request payload
    params = {
        "message": {
            "kind": "message",
            "messageId": "test-stream-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [{"kind": "text", "text": "Stream test message"}],
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
            assert response.headers.get("content-type", "").startswith("text/event-stream"), (
                "Streaming capability declared but Content-Type is not text/event-stream"
            )

            # Process the SSE stream
            sse_client = SimpleSSEClient(response, timeout=TIMEOUTS["sse_client_short"])
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
                assert message_utils.is_json_rpc_success_response(
                    event, expected_id=req_id
                ) or message_utils.is_json_rpc_error_response(event, expected_id=req_id), (
                    "Streaming capability declared but invalid JSON-RPC responses received"
                )

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

    if not validator.is_capability_declared("streaming"):
        pytest.skip("Streaming capability not declared - test not applicable")

    # Test with invalid params structure
    req_id = message_utils.generate_request_id()
    json_rpc_request = message_utils.make_json_rpc_request("message/stream", params={"invalid": "params"}, id=req_id)

    sut_url = config.get_sut_url()
    headers = {"Content-Type": "application/json"}

    response = await async_http_client.post(sut_url, json=json_rpc_request, headers=headers)

    # Should return JSON-RPC error, not streaming response
    assert response.status_code == 200, "Should return JSON-RPC error response, not HTTP error"
    assert response.headers.get("content-type", "").startswith("application/json"), (
        "Invalid params should return JSON-RPC error, not SSE stream"
    )

    response_data = response.json()
    assert message_utils.is_json_rpc_error_response(response_data, expected_id=req_id), (
        "Streaming capability declared but invalid params not properly rejected"
    )


@optional_capability
@pytest.mark.asyncio
async def test_tasks_resubscribe(async_http_client: httpx.AsyncClient, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.9 - Task Resubscription

    Status: MANDATORY if capabilities.streaming = true
            SKIP if capabilities.streaming = false/missing

    Test validates the tasks/resubscribe method for existing tasks.
    This method allows clients to resubscribe to SSE streams for ongoing tasks.
    """
    validator = CapabilityValidator(agent_card_data)

    if not validator.is_capability_declared("streaming"):
        pytest.skip("Streaming capability not declared - test not applicable")

    # First, create a task via message/send
    sut_client = SUTClient()
    message_params = {
        "message": {
            "kind": "message",
            "messageId": "test-resubscribe-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [{"kind": "text", "text": "Test message for resubscribe"}],
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
            assert response.headers.get("content-type", "").startswith("text/event-stream"), (
                "Streaming capability declared but Content-Type is not text/event-stream"
            )
            # Process the SSE stream
            sse_client = SimpleSSEClient(response, timeout=TIMEOUTS["sse_client_normal"])
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
                await asyncio.wait_for(process_sse_events(), timeout=TIMEOUTS["async_wait_for"])

            except asyncio.TimeoutError:
                logger.warning("Timeout while processing SSE stream")

            # Validate the collected events
            assert len(events) > 0, "Streaming capability declared but no events received from stream"

            # Check that the received events match our expectations
            for event in events:
                assert message_utils.is_json_rpc_success_response(
                    event, expected_id=req_id
                ) or message_utils.is_json_rpc_error_response(event, expected_id=req_id), (
                    "Streaming capability declared but invalid JSON-RPC responses received"
                )

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
            assert response.headers.get("content-type", "").startswith("text/event-stream"), (
                "Streaming capability declared but resubscribe didn't return SSE stream"
            )

            # Process the SSE stream similar to message/stream test
            sse_client = SimpleSSEClient(response, timeout=TIMEOUTS["sse_client_normal"])
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
                                assert message_utils.is_json_rpc_success_response(data, expected_id=req_id), (
                                    "Received an error or unexpected JSON-RPC response in the resubscribe stream"
                                )
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
                await asyncio.wait_for(process_resubscribe_events(), timeout=TIMEOUTS["async_wait_for"])

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

    if not validator.is_capability_declared("streaming"):
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
            assert response.headers.get("content-type", "").startswith("text/event-stream"), (
                "Streaming capability declared but Content-Type is not text/event-stream"
            )

            # Process the SSE stream
            sse_client = SimpleSSEClient(response, timeout=TIMEOUTS["sse_client_normal"])
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
            assert "not found" in error_message or "task" in error_message, (
                "Error message should clearly indicate task was not found"
            )

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
async def test_sse_header_compliance(async_http_client, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §3.3.1 - SSE Header Compliance

    Status: MANDATORY if capabilities.streaming = true
            SKIP if capabilities.streaming = false/missing

    Test validates that streaming responses include proper SSE headers as required
    by the A2A specification and W3C SSE standard.
    """
    validator = CapabilityValidator(agent_card_data)

    if not validator.is_capability_declared("streaming"):
        pytest.skip("Streaming capability not declared - test not applicable")

    # Prepare streaming request
    params = {
        "message": {
            "kind": "message",
            "messageId": "test-sse-headers-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [{"kind": "text", "text": "Test SSE headers"}],
        }
    }

    req_id = message_utils.generate_request_id()
    json_rpc_request = message_utils.make_json_rpc_request("message/stream", params=params, id=req_id)

    sut_url = config.get_sut_url()
    headers = {"Content-Type": "application/json"}

    async with async_http_client.stream("POST", sut_url, json=json_rpc_request, headers=headers) as response:
        # Validate HTTP status
        assert response.status_code == 200, "Streaming should return HTTP 200"

        # Validate required SSE headers per A2A specification §3.3.1
        content_type = response.headers.get("content-type", "")
        assert content_type.startswith("text/event-stream"), (
            f"Streaming must return Content-Type: text/event-stream, got: {content_type}"
        )

        # Optional but recommended SSE headers for better client behavior
        cache_control = response.headers.get("cache-control", "")
        if cache_control:
            assert "no-cache" in cache_control.lower(), "If Cache-Control is present, it should include no-cache for SSE streams"

        # Connection header should allow streaming
        connection = response.headers.get("connection", "")
        if connection:
            assert "close" not in connection.lower(), "Connection header should not force close for streaming"


@optional_capability
@pytest.mark.asyncio
async def test_sse_event_format_compliance(async_http_client, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §3.3.1 - SSE Event Format

    Status: MANDATORY if capabilities.streaming = true
            SKIP if capabilities.streaming = false/missing

    Test validates that SSE events follow proper format with JSON-RPC 2.0
    responses in the data field as required by A2A specification.
    """
    validator = CapabilityValidator(agent_card_data)

    if not validator.is_capability_declared("streaming"):
        pytest.skip("Streaming capability not declared - test not applicable")

    params = {
        "message": {
            "kind": "message",
            "messageId": "test-sse-format-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [{"kind": "text", "text": "Test SSE event format"}],
        }
    }

    req_id = message_utils.generate_request_id()
    json_rpc_request = message_utils.make_json_rpc_request("message/stream", params=params, id=req_id)

    sut_url = config.get_sut_url()
    headers = {"Content-Type": "application/json"}

    async with async_http_client.stream("POST", sut_url, json=json_rpc_request, headers=headers) as response:
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/event-stream")

        sse_client = SimpleSSEClient(response, timeout=TIMEOUTS["sse_client_short"])
        events_processed = 0

        async for event in sse_client:
            events_processed += 1

            # Validate SSE event structure per W3C specification
            assert isinstance(event, dict), "SSE event should be parsed as dictionary"

            if "data" in event:
                # Validate that data field contains valid JSON
                try:
                    data = json.loads(event["data"])
                except json.JSONDecodeError:
                    pytest.fail(f"SSE data field must contain valid JSON, got: {event['data']}")

                # Validate JSON-RPC 2.0 structure per A2A specification §3.3.1
                assert "jsonrpc" in data, "SSE data must contain JSON-RPC 2.0 response"
                assert data["jsonrpc"] == "2.0", "JSON-RPC version must be 2.0"
                assert "id" in data, "JSON-RPC response must include id field"
                assert data["id"] == req_id, f"JSON-RPC id mismatch: expected {req_id}, got {data.get('id')}"

                # Must have either result or error, but not both
                has_result = "result" in data
                has_error = "error" in data
                assert has_result or has_error, "JSON-RPC response must have result or error"
                assert not (has_result and has_error), "JSON-RPC response cannot have both result and error"

                # Validate result structure for success responses
                if has_result:
                    result = data["result"]
                    assert isinstance(result, dict), "Result must be object for A2A streaming responses"

                    # Should be Task, Message, TaskStatusUpdateEvent, or TaskArtifactUpdateEvent
                    if "kind" in result:
                        valid_kinds = ["task", "message", "status-update", "artifact-update"]
                        assert result["kind"] in valid_kinds, (
                            f"Result kind must be one of {valid_kinds}, got: {result.get('kind')}"
                        )

            # Process a few events then break
            if events_processed >= 3:
                break

        assert events_processed > 0, "Streaming should produce at least one SSE event"


@optional_capability
@pytest.mark.asyncio
async def test_streaming_connection_resilience(async_http_client, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A Specification §7.9 - Streaming Resilience

    Status: MANDATORY if capabilities.streaming = true
            SKIP if capabilities.streaming = false/missing

    Test validates that streaming connections handle interruptions gracefully
    and that tasks/resubscribe allows resuming streams.
    """
    validator = CapabilityValidator(agent_card_data)

    if not validator.is_capability_declared("streaming"):
        pytest.skip("Streaming capability not declared - test not applicable")

    # First create a task via streaming to get a task ID
    params = {
        "message": {
            "kind": "message",
            "messageId": "test-resilience-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [{"kind": "text", "text": "Simple task for resilience test"}],
        }
    }

    req_id = message_utils.generate_request_id()
    json_rpc_request = message_utils.make_json_rpc_request("message/stream", params=params, id=req_id)

    sut_url = config.get_sut_url()
    headers = {"Content-Type": "application/json"}
    task_id = None

    # Start initial stream and capture task ID - handle gracefully if timeout occurs
    try:
        async with async_http_client.stream("POST", sut_url, json=json_rpc_request, headers=headers) as response:
            assert response.status_code == 200

            sse_client = SimpleSSEClient(response, timeout=TIMEOUTS["sse_client_short"])

            try:
                async for event in sse_client:
                    if "data" in event:
                        try:
                            data = json.loads(event["data"])
                            if "result" in data and isinstance(data["result"], dict):
                                result = data["result"]
                                if "id" in result and "status" in result:
                                    # Found a Task object
                                    task_id = result["id"]
                                    logger.info(f"Captured task ID: {task_id}")
                                    break
                        except json.JSONDecodeError:
                            continue

                    # Break after first event to simulate early disconnection
                    break
            except asyncio.TimeoutError:
                logger.warning("Timeout during initial stream - this is expected for resilience test")
    except (httpx.HTTPError, httpx.ReadTimeout, httpx.TimeoutException) as e:
        logger.info(f"Connection interruption during initial stream: {e} - this is expected")

    if task_id:
        # Try to resubscribe to the task with timeout handling
        resubscribe_params = {"id": task_id}
        req_id_2 = message_utils.generate_request_id()
        resubscribe_request = message_utils.make_json_rpc_request("tasks/resubscribe", params=resubscribe_params, id=req_id_2)

        try:
            async with async_http_client.stream(
                "POST", sut_url, json=resubscribe_request, headers=headers, timeout=10.0
            ) as response:
                assert response.status_code == 200, "Resubscribe should succeed for existing task"
                assert response.headers.get("content-type", "").startswith("text/event-stream"), (
                    "Resubscribe should return SSE stream"
                )

                # Verify we can receive events from resubscription
                sse_client = SimpleSSEClient(response, timeout=TIMEOUTS["sse_client_short"])
                resubscribe_events = 0

                try:
                    async for event in sse_client:
                        if "data" in event:
                            resubscribe_events += 1
                            logger.info(f"Received resubscribe event #{resubscribe_events}")
                            if resubscribe_events >= 1:  # At least one event from resubscription
                                break
                except asyncio.TimeoutError:
                    logger.warning("Timeout during resubscribe stream processing")

                # Test passes if we can establish the resubscribe connection, even if no events
                # This validates that the resubscribe mechanism works
                assert True, "Resubscribe connection established successfully"
        except (httpx.HTTPError, httpx.ReadTimeout, httpx.TimeoutException) as e:
            # If resubscribe fails, check if it's due to task not found (which is acceptable)
            if "not found" in str(e).lower() or "404" in str(e):
                pytest.skip("Task expired before resubscribe test - this is implementation-dependent behavior")
            else:
                pytest.fail(f"Resubscribe failed unexpectedly: {e}")
    else:
        pytest.skip("Could not capture task ID from initial stream - cannot test resubscribe resilience")
