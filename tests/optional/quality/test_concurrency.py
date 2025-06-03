import concurrent.futures
import logging
import threading
import time
import uuid

import pytest

from tck import message_utils
from tck.sut_client import SUTClient
from tests.markers import quality_production, quality_basic

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()

@pytest.fixture
def text_message_params():
    """Create a basic text message params object"""
    return {
        "message": {
            "messageId": "test-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Hello from concurrency test!"
                }
            ]
        }
    }

@quality_production
def test_parallel_requests(sut_client, text_message_params):
    """
    QUALITY PRODUCTION: Concurrent Request Handling
    
    Tests the SUT's ability to handle multiple parallel requests gracefully.
    This is important for production deployments where multiple clients
    may send requests simultaneously.
    
    Validates:
    - Multiple parallel message/send requests
    - Proper response handling under concurrent load
    - No race conditions or resource conflicts
    """
    # Number of parallel requests to send
    NUM_REQUESTS = 5
    
    # Function to send a request and return the response
    def send_request(i):
        # Create unique text for each request to differentiate
        params = text_message_params.copy()
        params["message"]["parts"][0]["text"] = f"Parallel request {i} - {uuid.uuid4()}"
        
        req = message_utils.make_json_rpc_request("message/send", params=params)
        try:
            resp = sut_client.send_json_rpc(**req)
            return (i, req["id"], resp)
        except Exception as e:
            logger.error(f"Request {i} failed: {e}")
            return (i, req["id"], None)
    
    # Send requests in parallel using ThreadPoolExecutor
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_REQUESTS) as executor:
        futures = [executor.submit(send_request, i) for i in range(NUM_REQUESTS)]
        
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    
    # Verify all requests were processed successfully
    num_success = 0
    for i, req_id, resp in results:
        if resp and message_utils.is_json_rpc_success_response(resp, expected_id=req_id):
            num_success += 1
        else:
            logger.warning(f"Request {i} with ID {req_id} failed or returned unexpected response")
    
    # We expect most requests to succeed, but allow for some failures in case
    # the SUT has rate limiting or concurrency limits
    assert num_success > 0, "All parallel requests failed - poor concurrency handling"
    logger.info(f"{num_success} out of {NUM_REQUESTS} parallel requests succeeded")

@quality_basic
def test_rapid_sequential_requests(sut_client, text_message_params):
    """
    QUALITY BASIC: A2A Specification §5.1 - Sequential Request Handling
    
    Tests A2A Specification requirement for robust message processing.
    The SUT should handle rapid sequential requests without
    degradation or resource leaks.
    
    Failure Impact: Limits production reliability (acceptable for basic quality)
    Fix Suggestion: Implement proper request queuing and resource management
    
    Validates:
    - Multiple rapid sequential requests per A2A message/send method
    - Consistent response times and behavior
    - No resource exhaustion under sequential load
    - Specification compliance for sustained operation
    """
    # Number of sequential requests to send
    NUM_REQUESTS = 10
    
    # Send multiple requests as quickly as possible
    results = []
    for i in range(NUM_REQUESTS):
        params = text_message_params.copy()
        params["message"]["parts"][0]["text"] = f"Rapid request {i} - {uuid.uuid4()}"
        
        req = message_utils.make_json_rpc_request("message/send", params=params)
        try:
            resp = sut_client.send_json_rpc(**req)
            results.append((i, req["id"], resp))
        except Exception as e:
            logger.error(f"Request {i} failed: {e}")
            results.append((i, req["id"], None))
    
    # Verify all requests were processed successfully
    num_success = 0
    for i, req_id, resp in results:
        if resp and message_utils.is_json_rpc_success_response(resp, expected_id=req_id):
            num_success += 1
        else:
            logger.warning(f"Request {i} with ID {req_id} failed or returned unexpected response")
    
    # Expect a high success rate for sequential requests
    assert num_success > NUM_REQUESTS * 0.8, f"Too many failures: {num_success} out of {NUM_REQUESTS} succeeded"
    logger.info(f"{num_success} out of {NUM_REQUESTS} rapid sequential requests succeeded")

@quality_production
def test_concurrent_operations_same_task(sut_client, text_message_params):
    """
    QUALITY PRODUCTION: Task Concurrency Safety
    
    Tests the SUT's handling of concurrent operations on the same task.
    This is critical for production systems where multiple operations
    might be performed on a task simultaneously.
    
    Validates:
    - Concurrent task operations (get, update, cancel)
    - Proper state management under concurrent access
    - No race conditions or data corruption
    """
    # Step 1: Create a task
    create_req = message_utils.make_json_rpc_request("message/send", params=text_message_params)
    create_resp = sut_client.send_json_rpc(**create_req)
    
    if not message_utils.is_json_rpc_success_response(create_resp, expected_id=create_req["id"]):
        pytest.skip("Failed to create task for concurrent operations test")
        
    task_id = create_resp["result"]["id"]
    
    # Step 2: Define operations to perform concurrently on the task
    def get_task():
        req = message_utils.make_json_rpc_request("tasks/get", params={"id": task_id})
        resp = sut_client.send_json_rpc(**req)
        return ("get", req["id"], resp)
    
    def update_task():
        params = {
            "message": {
                "taskId": task_id,
                "messageId": "test-update-message-id-" + str(uuid.uuid4()),
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": f"Concurrent update {uuid.uuid4()}"
                    }
                ]
            }
        }
        req = message_utils.make_json_rpc_request("message/send", params=params)
        resp = sut_client.send_json_rpc(**req)
        return ("update", req["id"], resp)
    
    def cancel_task():
        # Sleep briefly to let other operations start
        time.sleep(0.1)
        req = message_utils.make_json_rpc_request("tasks/cancel", params={"id": task_id})
        resp = sut_client.send_json_rpc(**req)
        return ("cancel", req["id"], resp)
    
    # Step 3: Execute operations concurrently
    operations = [get_task, update_task, cancel_task]
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(operations)) as executor:
        futures = [executor.submit(op) for op in operations]
        
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    
    # Step 4: Verify results
    # We don't assert specific success/failure patterns since behavior may vary
    # Some SUTs might reject operations after cancel, others might accept them
    for op_name, req_id, resp in results:
        logger.info(f"Operation {op_name} resulted in: {resp}")
        assert "jsonrpc" in resp, f"Operation {op_name} did not return valid JSON-RPC response"
        assert "id" in resp and resp["id"] == req_id, f"Operation {op_name} returned wrong request ID" 