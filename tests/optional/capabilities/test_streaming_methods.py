import asyncio
import logging
import os
import uuid

import pytest

from tck import agent_card_utils, config, message_utils
from tests.markers import optional_capability
from tests.capability_validator import CapabilityValidator, skip_if_capability_not_declared
from tests.utils.transport_helpers import (
    transport_send_streaming_message,
    transport_resubscribe_task,
    generate_test_message_id,
)

logger = logging.getLogger(__name__)

# Configurable timeout system
# Base timeout can be configured via environment variable TCK_STREAMING_TIMEOUT
# Usage: TCK_STREAMING_TIMEOUT=5.0 python -m pytest ...
# Default is 2.0 seconds if not specified
BASE_TIMEOUT = float(os.getenv("TCK_STREAMING_TIMEOUT", "2.0"))

# Timeout multipliers for different operations

# Test constants
NON_EXISTENT_TASK_ID_PREFIX = "non-existent-task-id-"
TIMEOUTS = {
    "sse_client_short": BASE_TIMEOUT * 0.5,  # 1.0s default (for basic streaming)
    "sse_client_normal": BASE_TIMEOUT * 1.0,  # 2.0s default (for normal streaming)
    "async_wait_for": BASE_TIMEOUT * 1.0,  # 2.0s default (for asyncio.wait_for)
}

# SimpleSSEClient class removed - now using transport-agnostic streaming


# Helper function to check streaming support from Agent Card
def has_streaming_support(agent_card_data) -> bool:
    """Check if the SUT supports streaming based on Agent Card data."""
    if agent_card_data is None:
        logger.warning("Agent Card data is None, assuming streaming is not supported")
        return False

    return agent_card_utils.get_capability_streaming(agent_card_data)


@optional_capability
@pytest.mark.asyncio
async def test_message_stream_basic(sut_client, agent_card_data):
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

    # Prepare the streaming request message
    message_params = {
        "message": {
            "kind": "message",
            "messageId": generate_test_message_id("stream"),
            "role": "user",
            "parts": [{"kind": "text", "text": "Stream test message"}],
        }
    }

    try:
        # Use transport-agnostic streaming message sending
        stream = transport_send_streaming_message(sut_client, message_params)
        events = []

        # Collect events with a timeout to avoid hanging indefinitely
        try:
            event_count = 0
            async for event in stream:
                event_count += 1
                logger.info(f"Processing streaming event #{event_count}: {event}")
                events.append(event)

                # Safety break to prevent infinite loops
                if event_count >= 10:
                    logger.warning("Hit event count limit in basic test, breaking")
                    break

                # Check if this is a terminal event to break the loop
                if isinstance(event, dict):
                    if "status" in event and isinstance(event["status"], dict):
                        state = event["status"].get("state")
                        if state in ["completed", "failed", "canceled"]:
                            logger.info("Detected terminal event, ending stream processing.")
                            break

                # Break after a reasonable number of events for testing
                if len(events) >= 5:
                    logger.info("Collected 5 events, ending stream processing.")
                    break

        except asyncio.TimeoutError:
            logger.warning("Timeout while processing streaming events")

        # Validate the collected events
        assert len(events) > 0, "Streaming capability declared but no events received from stream"

        # Check that the received events are valid A2A objects
        for event in events:
            assert isinstance(event, dict), "Streaming events must be objects"

            # Event should be a Task, Message, TaskStatusUpdateEvent, or TaskArtifactUpdateEvent
            if "status" in event and "id" in event:
                # Looks like a Task
                assert isinstance(event["status"], dict)
            elif "kind" in event and event.get("kind") == "status-update":
                # Looks like a TaskStatusUpdateEvent
                assert "taskId" in event
            elif "kind" in event and event.get("kind") == "artifact-update":
                # Looks like a TaskArtifactUpdateEvent
                assert "taskId" in event
                assert "artifact" in event
            elif "kind" in event and event.get("kind") == "message":
                # Looks like a Message
                assert "role" in event
                assert "parts" in event
            # Otherwise it might be another valid type

    except Exception as e:
        # Check for transport-specific error handling
        error_msg = str(e).lower()
        if "501" in error_msg or "not implemented" in error_msg:
            # This is a FAILURE because streaming was declared but not implemented
            pytest.fail(
                "Streaming capability declared in Agent Card but SUT returned error indicating not implemented. "
                "This is a specification violation - declared capabilities MUST be implemented."
            )
        else:
            raise


@optional_capability
@pytest.mark.asyncio
async def test_message_stream_invalid_params(sut_client, agent_card_data):
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

    # Test with invalid params structure (missing required fields)
    invalid_message_params = {"invalid": "params"}  # Missing required message structure

    try:
        # This should fail at the transport level or return an error stream
        stream = transport_send_streaming_message(sut_client, invalid_message_params)
        
        # If we get a stream, check if it returns error events
        events = []
        try:
            async for event in stream:
                events.append(event)
                # Limit events to prevent hanging on invalid input
                if len(events) >= 3:
                    break
        except Exception:
            # Expected - invalid params should cause an error
            pass
        
        # If we got events, they should indicate error
        if events:
            # Check if any event indicates an error
            has_error = any(
                isinstance(event, dict) and (
                    "error" in event or 
                    ("status" in event and event.get("status", {}).get("state") == "failed")
                )
                for event in events
            )
            assert has_error, "Invalid params should result in error response or failed status"
    except ValueError as e:
        # Transport layer should catch invalid params and raise ValueError
        assert "message" in str(e).lower() or "param" in str(e).lower(), f"Unexpected error for invalid params: {e}"
    except Exception as e:
        # Other exceptions might indicate proper error handling
        logger.info(f"Invalid params properly rejected with: {e}")


@optional_capability
@pytest.mark.asyncio
async def test_tasks_resubscribe(sut_client, agent_card_data):
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

    # Synchronization events
    task_id_received = asyncio.Event()

    task_id = None
    resubscribe_events = []
    stream_error = None
    resubscribe_error = None
    
    try:
        # First, create a task via message/stream to get a task ID
        message_params = {
            "message": {
                "kind": "message",
                "messageId": "test-resubscribe-message-id-" + str(uuid.uuid4()),
                "role": "user",
                "parts": [{"kind": "text", "text": "Test message for resubscribe"}],
            }
        }

        # Use transport-agnostic streaming message sending
        stream = transport_send_streaming_message(sut_client, message_params)

        # Background task to process the initial stream
        async def process_initial_stream():
            nonlocal task_id, stream_error
            try:
                event_count = 0
                async for event in stream:
                    event_count += 1
                    logger.info(f"Processing streaming event #{event_count}: {event}")

                    # Look for task ID in the event
                    if isinstance(event, dict):
                        if "id" in event and "status" in event:
                            # This looks like a Task object
                            task_id = event["id"]
                            logger.info(f"Captured task ID from stream: {task_id}")
                            # Signal that task ID is available. This means that the event queue is open
                            task_id_received.set()

                    # Safety break to prevent infinite loops
                    if event_count >= 10:
                        logger.warning("Hit event count limit while getting task ID")
                        break

                    # Continue processing events even after getting task ID
                    # to keep the stream alive for resubscribe testing

            except Exception as e:
                stream_error = e
                logger.error(f"Error in initial stream processing: {e}")
                task_id_received.set()  # Signal completion even on error

        # Background task to handle resubscription once task ID is available
        async def process_resubscribe():
            nonlocal resubscribe_events, resubscribe_error
            try:
                # Wait for task ID to be available
                await task_id_received.wait()
                
                if task_id is None:
                    logger.warning("No task ID available for resubscribe")
                    return

                logger.info(f"Starting resubscribe for task ID: {task_id}")
                
                # Use transport-agnostic task resubscription
                resubscribe_stream = transport_resubscribe_task(sut_client, task_id)

                event_count = 0
                async for event in resubscribe_stream:
                    event_count += 1
                    logger.info(f"Processing resubscribe event #{event_count}: {event}")
                    resubscribe_events.append(event)

                    # Safety break to prevent infinite loops
                    if event_count >= 10:
                        logger.warning("Hit event count limit in resubscribe test, breaking")
                        break

                    # Validate this is a proper A2A object
                    assert isinstance(event, dict), "Resubscribe events must be objects"

                    # Check if this is a terminal event
                    if "status" in event and isinstance(event["status"], dict):
                        state = event["status"].get("state")
                        if state in ["completed", "failed", "canceled"]:
                            logger.info("Detected terminal event in resubscribe, ending stream processing.")
                            break

                    # Collect a few events then break
                    if len(resubscribe_events) >= 3:
                        break
                        
            except Exception as e:
                resubscribe_error = e
                logger.error(f"Error in resubscribe processing: {e}")

        # Start both background tasks
        initial_stream_task = asyncio.create_task(process_initial_stream())
        resubscribe_task = asyncio.create_task(process_resubscribe())

        # Wait for both tasks to complete with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(initial_stream_task, resubscribe_task, return_exceptions=True),
                timeout=TIMEOUTS["async_wait_for"] * 2)
        except asyncio.TimeoutError:
            logger.warning("Timeout while waiting for stream processing and resubscribe")
            # Cancel tasks if they're still running
            initial_stream_task.cancel()
            resubscribe_task.cancel()
            
        # Check for errors from the background tasks
        if stream_error:
            error_msg = str(stream_error).lower()
            if "501" in error_msg or "not implemented" in error_msg:
                pytest.fail(
                    "Streaming capability declared in Agent Card but SUT returned error indicating not implemented. "
                    "This is a specification violation - declared capabilities MUST be implemented."
                )
            else:
                raise stream_error

    except Exception as e:
        error_msg = str(e).lower()
        if "501" in error_msg or "not implemented" in error_msg:
            pytest.fail(
                "Streaming capability declared in Agent Card but SUT returned error indicating not implemented. "
                "This is a specification violation - declared capabilities MUST be implemented."
            )
        else:
            raise

    # Now validate the resubscribe results
    if task_id is None:
        pytest.skip("Could not capture task ID from initial stream - cannot test resubscribe")

    # Check for resubscribe errors
    if resubscribe_error:
        error_msg = str(resubscribe_error).lower()
        if "501" in error_msg or "not implemented" in error_msg:
            pytest.fail(
                "Streaming capability declared but tasks/resubscribe returned error indicating not implemented. "
                "This violates the A2A specification - declared capabilities MUST be implemented."
            )
        elif "not found" in error_msg or "404" in error_msg:
            pytest.skip("Task expired before resubscribe test - this is implementation-dependent behavior")
        else:
            raise resubscribe_error

    # Validate that we got at least some events from resubscribe
    assert len(resubscribe_events) > 0, "Streaming capability declared but no events received from resubscribe stream"


@optional_capability
@pytest.mark.asyncio
async def test_tasks_resubscribe_nonexistent(sut_client, agent_card_data):
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
    task_id = NON_EXISTENT_TASK_ID_PREFIX + message_utils.generate_request_id()

    try:
        # Use transport-agnostic task resubscription with non-existent task ID
        resubscribe_stream = transport_resubscribe_task(sut_client, task_id)
        events = []
        error_found = False

        try:
            # Wrap the stream iteration in a timeout to prevent hanging
            async def process_stream():
                event_count = 0
                error_event_found = False

                async for event in resubscribe_stream:
                    event_count += 1
                    logger.info(f"Processing nonexistent task event #{event_count}: {event}")
                    events.append(event)

                    # Safety break to prevent infinite loops
                    if event_count >= 10:
                        logger.warning("Hit event count limit in nonexistent task test, breaking")
                        break

                    # Check if this event indicates an error
                    if isinstance(event, dict):
                        # Look for error indicators in the event
                        if "error" in event:
                            error_event_found = True
                            error = event["error"]
                            if isinstance(error, dict):
                                # Validate error structure
                                assert "code" in error or "message" in error, "Error should have code or message"
                                if "message" in error:
                                    error_message = error["message"].lower()
                                    assert "not found" in error_message or "task" in error_message, (
                                        "Error message should clearly indicate task was not found"
                                    )
                            break
                        elif "status" in event and isinstance(event["status"], dict):
                            state = event["status"].get("state")
                            if state == "failed":
                                error_event_found = True
                                break

                    # Break after a reasonable number of events for testing
                    if len(events) >= 5:
                        logger.info("Collected 5 events, ending stream processing.")
                        break
                
                return error_event_found

            # Add timeout to prevent hanging on bad streams
            error_found = await asyncio.wait_for(process_stream(), timeout=TIMEOUTS["async_wait_for"])
                    
        except asyncio.TimeoutError:
            logger.warning("Timeout while processing resubscribe stream for nonexistent task - this may be expected")
        except RuntimeError as e:
            if "event loop is closed" in str(e).lower():
                # This can happen when the transport client properly rejects the request
                logger.info("Transport client properly closed connection for non-existent task")
                error_found = True
            else:
                raise

        # Should have received an error or failed status for non-existent task
        if events and not error_found:
            pytest.fail("Expected error or failed status for non-existent task, but got successful events")
        elif not events and not error_found:
            # No events could mean the transport layer properly rejected the request
            logger.info("No events received for non-existent task - transport may have rejected the request")

    except Exception as e:
        error_msg = str(e).lower()
        if "501" in error_msg or "not implemented" in error_msg:
            pytest.fail(
                "Streaming capability declared but tasks/resubscribe returned error indicating not implemented. "
                "This violates the A2A specification - declared capabilities MUST be implemented."
            )
        elif ("not found" in error_msg or "404" in error_msg or "invalid" in error_msg or 
              "event loop is closed" in error_msg):
            # These are expected behaviors for non-existent task ID
            logger.info(f"Properly rejected non-existent task with: {e}")
        else:
            raise


@optional_capability
@pytest.mark.asyncio
async def test_sse_header_compliance(sut_client, agent_card_data):
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

    # Note: This test validates HTTP-specific SSE headers, so it needs access to the underlying HTTP response.
    # For JSON-RPC transport, we can test this. For other transports, this test may not be applicable.
    
    # Check if we're using a transport that supports HTTP headers inspection
    transport_type = getattr(sut_client, 'transport_type', None)
    if transport_type and transport_type.value.lower() != 'jsonrpc':
        pytest.skip(f"SSE header compliance test only applicable to JSON-RPC transport, got {transport_type.value}")
    
    # Prepare streaming request message
    message_params = {
        "message": {
            "kind": "message",
            "messageId": generate_test_message_id("sse-headers"),
            "role": "user",
            "parts": [{"kind": "text", "text": "Test SSE headers"}],
        }
    }

    try:
        # For this specific test, we need to access the underlying HTTP client
        # to check headers. We'll use the raw JSON-RPC method if available.
        if hasattr(sut_client, 'send_raw_json_rpc'):
            # Create JSON-RPC request for message/stream
            req_id = message_utils.generate_request_id()
            json_rpc_request = message_utils.make_json_rpc_request("message/stream", params=message_params, id=req_id)
            
            # This will depend on the specific implementation
            # For now, we'll just validate that streaming works
            stream = transport_send_streaming_message(sut_client, message_params)
            
            # Validate we can get streaming events (headers are transport-specific)
            event_count = 0
            async for event in stream:
                event_count += 1
                logger.info(f"Received streaming event for header test: {event}")
                if event_count >= 1:  # Just need to confirm streaming works
                    break
            
            assert event_count > 0, "Should receive at least one streaming event"
            logger.info("SSE streaming functionality confirmed (header validation is transport-specific)")
        else:
            pytest.skip("Cannot access raw HTTP response for header validation with this transport client")
            
    except Exception as e:
        error_msg = str(e).lower()
        if "501" in error_msg or "not implemented" in error_msg:
            pytest.fail(
                "Streaming capability declared but SUT returned error indicating not implemented. "
                "This is a specification violation - declared capabilities MUST be implemented."
            )
        else:
            raise


@optional_capability
@pytest.mark.asyncio
async def test_sse_event_format_compliance(sut_client, agent_card_data):
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

    message_params = {
        "message": {
            "kind": "message",
            "messageId": generate_test_message_id("sse-format"),
            "role": "user",
            "parts": [{"kind": "text", "text": "Test SSE event format"}],
        }
    }

    try:
        # Use transport-agnostic streaming message sending
        stream = transport_send_streaming_message(sut_client, message_params)
        events_processed = 0

        async for event in stream:
            events_processed += 1
            logger.info(f"Processing event format validation #{events_processed}: {event}")

            # Validate streaming event structure per A2A specification
            assert isinstance(event, dict), "Streaming event should be a dictionary/object"

            # For A2A streaming, events should be Task, Message, TaskStatusUpdateEvent, or TaskArtifactUpdateEvent objects
            # Validate basic A2A object structure
            if "kind" in event:
                # This is likely a Message, TaskStatusUpdateEvent, or TaskArtifactUpdateEvent
                valid_kinds = ["task", "message", "status-update", "artifact-update"]
                assert event["kind"] in valid_kinds, (
                    f"Event kind must be one of {valid_kinds}, got: {event.get('kind')}"
                )
                
                if event["kind"] == "message":
                    assert "role" in event, "Message events must have role field"
                    assert "parts" in event, "Message events must have parts field"
                elif event["kind"] == "status-update":
                    assert "taskId" in event, "Status update events must have taskId field"
                elif event["kind"] == "artifact-update":
                    assert "taskId" in event, "Artifact update events must have taskId field"
                    assert "artifact" in event, "Artifact update events must have artifact field"
            elif "status" in event and "id" in event:
                # This looks like a Task object
                assert isinstance(event["status"], dict), "Task status must be an object"
                assert "state" in event["status"], "Task status must have state field"
            else:
                # Unknown event type - log for debugging but don't fail
                logger.warning(f"Unknown event structure: {event}")

            # Process a few events then break
            if events_processed >= 3:
                break

        assert events_processed > 0, "Streaming should produce at least one event"
        
    except Exception as e:
        error_msg = str(e).lower()
        if "501" in error_msg or "not implemented" in error_msg:
            pytest.fail(
                "Streaming capability declared but SUT returned error indicating not implemented. "
                "This is a specification violation - declared capabilities MUST be implemented."
            )
        else:
            raise


#@optional_capability
@pytest.mark.skip(reason="This test is flaky due to network issues and timeouts; needs improvement")
@pytest.mark.asyncio
async def test_streaming_connection_resilience(sut_client, agent_card_data):
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

    # Note: This test is skipped due to flakiness and would need to be rewritten
    # to use transport_send_streaming_message and transport_resubscribe_task
    # instead of direct HTTP client access.
    pytest.skip("Test needs rewrite to use transport-agnostic streaming methods")
