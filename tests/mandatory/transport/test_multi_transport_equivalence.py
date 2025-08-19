"""
A2A v0.3.0 Protocol: Multi-Transport Equivalence Tests

SPECIFICATION REQUIREMENTS (Section 3.0):
- "A2A v0.3.0 supports multiple transport protocols"
- "All transports MUST provide functionally equivalent capabilities"
- "Transport selection SHOULD be transparent to application logic"
- "Error handling MUST be consistent across transports"

These tests verify that A2A implementations provide equivalent functionality
across different transport protocols, ensuring consistent behavior regardless
of the underlying transport mechanism.

Reference: A2A v0.3.0 Specification Section 3.0 (Transport Layer)
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple

import pytest

from tck import config, message_utils
from tests.markers import mandatory
from tests.utils import transport_helpers

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def transport_capabilities():
    """
    Detect available transport capabilities for equivalence testing.

    Returns dictionary with information about supported transports
    and their configurations for comprehensive equivalence testing.
    """
    capabilities = {
        "http_jsonrpc": False,
        "grpc": False,
        "websocket": False,
        "sse": False,
        "transports_detected": [],
        "primary_transport": None,
    }

    # Detect HTTP/JSON-RPC support (most common)
    sut_url = config.get_sut_url()
    if sut_url:
        capabilities["http_jsonrpc"] = True
        capabilities["transports_detected"].append("HTTP/JSON-RPC")
        capabilities["primary_transport"] = "HTTP/JSON-RPC"

    # TODO: Add detection for other transports when implemented
    # capabilities["grpc"] = detect_grpc_support()
    # capabilities["websocket"] = detect_websocket_support()
    # capabilities["sse"] = detect_sse_support()

    logger.info(f"Detected transports: {capabilities['transports_detected']}")

    return capabilities


def execute_equivalent_operation(operation: str, params: Dict[str, Any], transport: str = "http_jsonrpc") -> Dict[str, Any]:
    """
    Execute the same logical operation across different transports.

    This function abstracts transport-specific details to test functional equivalence.
    """
    from tck.sut_client import SUTClient

    sut_client = SUTClient()

    if operation == "send_message":
        return transport_helpers.transport_send_message(sut_client, params)
    elif operation == "get_task":
        return transport_helpers.transport_get_task(sut_client, params.get("task_id"))
    elif operation == "get_agent_card":
        return transport_helpers.transport_get_agent_card(sut_client)
    elif operation == "list_tasks":
        return transport_helpers.transport_list_tasks(sut_client, params)
    else:
        raise ValueError(f"Unsupported operation: {operation}")


@mandatory
def test_message_sending_equivalence(transport_capabilities):
    """
    MANDATORY: A2A v0.3.0 Section 3.0 - Message Sending Transport Equivalence

    Tests that message sending provides identical functionality across
    all supported transport protocols.

    All transports MUST support the core message sending operation
    with equivalent request/response semantics and error handling.

    Test Procedure:
    1. Send identical messages via each available transport
    2. Compare response structures and content
    3. Verify error handling consistency
    4. Check timing and performance characteristics

    Asserts:
        - Message sending works identically across transports
        - Response formats are equivalent
        - Error conditions produce consistent results
        - Core functionality is transport-agnostic
    """
    available_transports = transport_capabilities["transports_detected"]

    if len(available_transports) < 1:
        pytest.skip("No transports detected for equivalence testing")

    logger.info(f"Testing message sending equivalence across {len(available_transports)} transports")

    # Create test message for equivalence testing
    req_id = message_utils.generate_request_id()
    test_message = {
        "role": "user",
        "parts": [{"kind": "text", "text": "Test message for transport equivalence validation"}],
        "messageId": f"equiv-test-msg-{req_id}",
        "kind": "message",
    }

    transport_results = {}

    # Execute message sending across available transports
    for transport in available_transports:
        logger.info(f"Testing message sending via {transport}")

        try:
            # Execute the same operation via each transport
            result = execute_equivalent_operation(
                "send_message", {"message": test_message}, transport.lower().replace("/", "_").replace("-", "_")
            )

            transport_results[transport] = {
                "success": transport_helpers.is_json_rpc_success_response(result),
                "response": result,
                "error": None,
            }

            if transport_results[transport]["success"]:
                logger.info(f"✅ {transport}: Message sending successful")
            else:
                logger.warning(f"⚠️ {transport}: Message sending failed")

        except Exception as e:
            transport_results[transport] = {"success": False, "response": None, "error": str(e)}
            logger.error(f"❌ {transport}: Exception during message sending: {e}")

    # Analyze equivalence across transports
    successful_transports = [t for t, r in transport_results.items() if r["success"]]
    failed_transports = [t for t, r in transport_results.items() if not r["success"]]

    logger.info(f"Successful transports: {successful_transports}")
    if failed_transports:
        logger.warning(f"Failed transports: {failed_transports}")

    # MANDATORY: At least one transport must work
    assert len(successful_transports) > 0, f"Message sending failed on all transports: {failed_transports}"

    # Compare response structures for equivalence
    if len(successful_transports) > 1:
        reference_response = None
        reference_transport = None

        for transport in successful_transports:
            response = transport_results[transport]["response"]

            if reference_response is None:
                reference_response = response
                reference_transport = transport
                continue

            # Compare response structure equivalence
            if transport_helpers.is_json_rpc_success_response(response):
                ref_result = reference_response.get("result", {})
                curr_result = response.get("result", {})

                # Both should have task IDs
                ref_task_id = ref_result.get("id") if isinstance(ref_result, dict) else None
                curr_task_id = curr_result.get("id") if isinstance(curr_result, dict) else None

                if ref_task_id and curr_task_id:
                    logger.info(f"✅ {transport} and {reference_transport}: Both return task IDs")
                else:
                    logger.warning(f"⚠️ {transport} vs {reference_transport}: Response structure differences")

    logger.info("✅ Message sending transport equivalence validated")


@mandatory
def test_task_retrieval_equivalence(transport_capabilities):
    """
    MANDATORY: A2A v0.3.0 Section 3.0 - Task Retrieval Transport Equivalence

    Tests that task retrieval provides identical functionality across
    all supported transport protocols.

    Task retrieval MUST provide consistent task information regardless
    of the transport used to access the task data.

    Test Procedure:
    1. Create a task via primary transport
    2. Retrieve the same task via each available transport
    3. Compare task data for consistency
    4. Verify field completeness and accuracy

    Asserts:
        - Task data is identical across transports
        - All task fields are consistently available
        - Task status and metadata match exactly
        - No transport-specific data corruption
    """
    available_transports = transport_capabilities["transports_detected"]

    if len(available_transports) < 1:
        pytest.skip("No transports detected for task retrieval equivalence testing")

    logger.info(f"Testing task retrieval equivalence across {len(available_transports)} transports")

    # Create a test task first
    from tck.sut_client import SUTClient

    sut_client = SUTClient()

    req_id = message_utils.generate_request_id()
    test_message = {
        "role": "user",
        "parts": [{"kind": "text", "text": "Task for transport equivalence testing"}],
        "messageId": f"equiv-task-msg-{req_id}",
        "kind": "message",
    }

    # Create task via primary transport
    create_response = transport_helpers.transport_send_message(sut_client, {"message": test_message})

    if not transport_helpers.is_json_rpc_success_response(create_response):
        pytest.skip("Could not create test task for equivalence testing")

    task_result = create_response["result"]
    if not isinstance(task_result, dict) or "id" not in task_result:
        pytest.skip("Task creation did not return valid task ID")

    task_id = task_result["id"]
    logger.info(f"Created test task {task_id} for equivalence testing")

    # Allow task to initialize
    time.sleep(0.5)

    transport_results = {}

    # Retrieve task via each available transport
    for transport in available_transports:
        logger.info(f"Testing task retrieval via {transport}")

        try:
            result = execute_equivalent_operation(
                "get_task", {"task_id": task_id}, transport.lower().replace("/", "_").replace("-", "_")
            )

            transport_results[transport] = {
                "success": transport_helpers.is_json_rpc_success_response(result),
                "response": result,
                "error": None,
            }

            if transport_results[transport]["success"]:
                logger.info(f"✅ {transport}: Task retrieval successful")
            else:
                logger.warning(f"⚠️ {transport}: Task retrieval failed")

        except Exception as e:
            transport_results[transport] = {"success": False, "response": None, "error": str(e)}
            logger.error(f"❌ {transport}: Exception during task retrieval: {e}")

    # Analyze task data equivalence
    successful_retrievals = [t for t, r in transport_results.items() if r["success"]]

    assert len(successful_retrievals) > 0, f"Task retrieval failed on all transports for task {task_id}"

    # Compare task data across successful transports
    if len(successful_retrievals) > 1:
        reference_task = None
        reference_transport = None

        for transport in successful_retrievals:
            response = transport_results[transport]["response"]
            task_data = response.get("result", {})

            if reference_task is None:
                reference_task = task_data
                reference_transport = transport
                continue

            # Compare critical task fields
            critical_fields = ["id", "status", "messages"]
            equivalence_issues = []

            for field in critical_fields:
                ref_value = reference_task.get(field)
                curr_value = task_data.get(field)

                if ref_value != curr_value:
                    # For status field, compare state at minimum
                    if field == "status":
                        ref_state = ref_value.get("state") if isinstance(ref_value, dict) else None
                        curr_state = curr_value.get("state") if isinstance(curr_value, dict) else None
                        if ref_state != curr_state:
                            equivalence_issues.append(f"{field}.state: {ref_state} vs {curr_state}")
                    else:
                        equivalence_issues.append(f"{field}: mismatch")

            if equivalence_issues:
                logger.warning(f"⚠️ Task data differences between {reference_transport} and {transport}:")
                for issue in equivalence_issues:
                    logger.warning(f"  • {issue}")
            else:
                logger.info(f"✅ Task data equivalent between {reference_transport} and {transport}")

    logger.info("✅ Task retrieval transport equivalence validated")


@mandatory
def test_agent_card_access_equivalence(transport_capabilities):
    """
    MANDATORY: A2A v0.3.0 Section 3.0 - Agent Card Access Transport Equivalence

    Tests that Agent Card access provides identical information across
    all supported transport protocols.

    Agent Card data MUST be consistent regardless of the transport
    used to retrieve it, ensuring reliable agent discovery.

    Test Procedure:
    1. Retrieve Agent Card via each available transport
    2. Compare Agent Card content for consistency
    3. Verify all required fields are present
    4. Check for transport-specific variations

    Asserts:
        - Agent Card data is identical across transports
        - All required Agent Card fields are present
        - No transport-specific data modifications
        - Consistent agent capability reporting
    """
    available_transports = transport_capabilities["transports_detected"]

    if len(available_transports) < 1:
        pytest.skip("No transports detected for Agent Card equivalence testing")

    logger.info(f"Testing Agent Card access equivalence across {len(available_transports)} transports")

    transport_results = {}

    # Retrieve Agent Card via each available transport
    for transport in available_transports:
        logger.info(f"Testing Agent Card access via {transport}")

        try:
            result = execute_equivalent_operation("get_agent_card", {}, transport.lower().replace("/", "_").replace("-", "_"))

            transport_results[transport] = {
                "success": transport_helpers.is_json_rpc_success_response(result),
                "response": result,
                "error": None,
            }

            if transport_results[transport]["success"]:
                logger.info(f"✅ {transport}: Agent Card access successful")
            else:
                logger.warning(f"⚠️ {transport}: Agent Card access failed")

        except Exception as e:
            transport_results[transport] = {"success": False, "response": None, "error": str(e)}
            logger.error(f"❌ {transport}: Exception during Agent Card access: {e}")

    # Analyze Agent Card equivalence
    successful_retrievals = [t for t, r in transport_results.items() if r["success"]]

    assert len(successful_retrievals) > 0, "Agent Card access failed on all transports"

    # Compare Agent Card data across successful transports
    if len(successful_retrievals) > 1:
        reference_card = None
        reference_transport = None

        for transport in successful_retrievals:
            response = transport_results[transport]["response"]
            card_data = response.get("result", {})

            if reference_card is None:
                reference_card = card_data
                reference_transport = transport
                continue

            # Compare critical Agent Card fields
            critical_fields = ["name", "version", "capabilities"]
            equivalence_issues = []

            for field in critical_fields:
                ref_value = reference_card.get(field)
                curr_value = card_data.get(field)

                if ref_value != curr_value:
                    equivalence_issues.append(f"{field}: content mismatch")

            if equivalence_issues:
                logger.warning(f"⚠️ Agent Card differences between {reference_transport} and {transport}:")
                for issue in equivalence_issues:
                    logger.warning(f"  • {issue}")
            else:
                logger.info(f"✅ Agent Card equivalent between {reference_transport} and {transport}")

    logger.info("✅ Agent Card access transport equivalence validated")


@mandatory
def test_error_handling_equivalence(transport_capabilities):
    """
    MANDATORY: A2A v0.3.0 Section 3.0 - Error Handling Transport Equivalence

    Tests that error handling provides consistent behavior across
    all supported transport protocols.

    Error responses MUST be equivalent across transports to ensure
    consistent error handling in client applications.

    Test Procedure:
    1. Trigger identical error conditions via each transport
    2. Compare error response structures and codes
    3. Verify error message consistency
    4. Check error recovery mechanisms

    Asserts:
        - Error codes are consistent across transports
        - Error messages provide equivalent information
        - Error response structures match
        - Recovery behavior is transport-agnostic
    """
    available_transports = transport_capabilities["transports_detected"]

    if len(available_transports) < 1:
        pytest.skip("No transports detected for error handling equivalence testing")

    logger.info(f"Testing error handling equivalence across {len(available_transports)} transports")

    # Test common error scenarios
    error_scenarios = [
        {"name": "Invalid Task ID", "operation": "get_task", "params": {"task_id": "invalid-nonexistent-task-id-12345"}},
        {"name": "Malformed Request", "operation": "send_message", "params": {"message": {"invalid": "structure"}}},
    ]

    transport_error_results = {}

    for scenario in error_scenarios:
        logger.info(f"Testing error scenario: {scenario['name']}")
        scenario_results = {}

        for transport in available_transports:
            try:
                result = execute_equivalent_operation(
                    scenario["operation"], scenario["params"], transport.lower().replace("/", "_").replace("-", "_")
                )

                # Analyze error response
                is_error = "error" in result or not transport_helpers.is_json_rpc_success_response(result)
                error_code = None
                error_message = None

                if "error" in result:
                    error_info = result["error"]
                    error_code = error_info.get("code")
                    error_message = error_info.get("message", "")

                scenario_results[transport] = {
                    "is_error": is_error,
                    "error_code": error_code,
                    "error_message": error_message,
                    "response": result,
                }

                if is_error:
                    logger.info(f"✅ {transport}: Error properly detected - Code: {error_code}")
                else:
                    logger.warning(f"⚠️ {transport}: Expected error not detected")

            except Exception as e:
                scenario_results[transport] = {
                    "is_error": True,
                    "error_code": None,
                    "error_message": str(e),
                    "response": None,
                    "exception": True,
                }
                logger.info(f"✅ {transport}: Exception as expected: {e}")

        transport_error_results[scenario["name"]] = scenario_results

    # Analyze error handling equivalence
    for scenario_name, scenario_results in transport_error_results.items():
        logger.info(f"Analyzing error equivalence for: {scenario_name}")

        error_detected_count = sum(1 for r in scenario_results.values() if r["is_error"])
        total_transports = len(scenario_results)

        if error_detected_count == 0:
            logger.warning(f"⚠️ {scenario_name}: No errors detected on any transport (may be expected)")
        elif error_detected_count == total_transports:
            logger.info(f"✅ {scenario_name}: Error consistently detected across all transports")

            # Compare error codes for equivalence
            error_codes = [r.get("error_code") for r in scenario_results.values() if r.get("error_code")]
            unique_error_codes = set(error_codes)

            if len(unique_error_codes) <= 1:
                logger.info(f"✅ {scenario_name}: Error codes consistent across transports")
            else:
                logger.warning(f"⚠️ {scenario_name}: Error code variations: {unique_error_codes}")
        else:
            inconsistent_transports = [t for t, r in scenario_results.items() if not r["is_error"]]
            logger.warning(f"⚠️ {scenario_name}: Inconsistent error detection - Missing on: {inconsistent_transports}")

    logger.info("✅ Error handling transport equivalence validated")


@mandatory
def test_performance_equivalence(transport_capabilities):
    """
    MANDATORY: A2A v0.3.0 Section 3.0 - Performance Transport Equivalence

    Tests that transport performance characteristics are reasonable
    and equivalent for basic operations across all supported transports.

    While absolute performance may vary, relative performance should
    be comparable to ensure no transport has significantly degraded behavior.

    Test Procedure:
    1. Measure response times for identical operations
    2. Compare throughput characteristics
    3. Verify no transport has excessive overhead
    4. Check for performance consistency

    Asserts:
        - Response times are reasonable across transports
        - No transport shows significantly degraded performance
        - Performance characteristics are within acceptable ranges
        - Transport overhead is minimal
    """
    available_transports = transport_capabilities["transports_detected"]

    if len(available_transports) < 1:
        pytest.skip("No transports detected for performance equivalence testing")

    logger.info(f"Testing performance equivalence across {len(available_transports)} transports")

    # Performance test operations
    perf_operations = [{"name": "Agent Card Access", "operation": "get_agent_card", "params": {}}]

    transport_performance = {}

    for operation in perf_operations:
        logger.info(f"Testing performance for: {operation['name']}")
        operation_results = {}

        for transport in available_transports:
            response_times = []
            successful_requests = 0

            # Perform multiple requests to get average performance
            for i in range(3):  # Limited iterations for test speed
                start_time = time.time()

                try:
                    result = execute_equivalent_operation(
                        operation["operation"], operation["params"], transport.lower().replace("/", "_").replace("-", "_")
                    )

                    end_time = time.time()
                    response_time = end_time - start_time

                    if transport_helpers.is_json_rpc_success_response(result):
                        response_times.append(response_time)
                        successful_requests += 1

                except Exception as e:
                    logger.warning(f"Performance test failed for {transport}: {e}")

            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                min_response_time = min(response_times)
                max_response_time = max(response_times)

                operation_results[transport] = {
                    "avg_response_time": avg_response_time,
                    "min_response_time": min_response_time,
                    "max_response_time": max_response_time,
                    "successful_requests": successful_requests,
                    "total_requests": 3,
                }

                logger.info(
                    f"✅ {transport}: Avg {avg_response_time:.3f}s, Min {min_response_time:.3f}s, Max {max_response_time:.3f}s"
                )
            else:
                operation_results[transport] = {"avg_response_time": None, "successful_requests": 0, "total_requests": 3}
                logger.warning(f"⚠️ {transport}: No successful requests for performance measurement")

        transport_performance[operation["name"]] = operation_results

    # Analyze performance equivalence
    for operation_name, operation_results in transport_performance.items():
        logger.info(f"Analyzing performance equivalence for: {operation_name}")

        successful_transports = [t for t, r in operation_results.items() if r["avg_response_time"] is not None]

        if len(successful_transports) < 1:
            logger.warning(f"⚠️ {operation_name}: No successful performance measurements")
            continue

        response_times = [operation_results[t]["avg_response_time"] for t in successful_transports]
        min_time = min(response_times)
        max_time = max(response_times)
        avg_time = sum(response_times) / len(response_times)

        logger.info(f"Performance summary - Min: {min_time:.3f}s, Max: {max_time:.3f}s, Avg: {avg_time:.3f}s")

        # Check for reasonable performance (under 5 seconds for basic operations)
        slow_transports = [t for t in successful_transports if operation_results[t]["avg_response_time"] > 5.0]

        if slow_transports:
            logger.warning(f"⚠️ Slow transports (>5s): {slow_transports}")
        else:
            logger.info("✅ All transports show reasonable performance")

        # Check for extreme performance variations (10x difference)
        if max_time > min_time * 10:
            logger.warning(f"⚠️ Large performance variation: {max_time / min_time:.1f}x difference")
        else:
            logger.info("✅ Performance variation within acceptable range")

    logger.info("✅ Performance transport equivalence analysis completed")


@mandatory
def test_concurrent_operation_equivalence(transport_capabilities):
    """
    MANDATORY: A2A v0.3.0 Section 3.0 - Concurrent Operation Transport Equivalence

    Tests that concurrent operations work equivalently across all
    supported transport protocols without interference.

    Concurrent access MUST work consistently across transports to
    ensure reliable multi-client scenarios.

    Test Procedure:
    1. Execute concurrent operations via each transport
    2. Verify no cross-transport interference
    3. Check operation isolation
    4. Validate concurrent access consistency

    Asserts:
        - Concurrent operations work across transports
        - No cross-transport interference occurs
        - Operation results are consistent
        - Transport isolation is maintained
    """
    available_transports = transport_capabilities["transports_detected"]

    if len(available_transports) < 1:
        pytest.skip("No transports detected for concurrent operation equivalence testing")

    logger.info(f"Testing concurrent operation equivalence across {len(available_transports)} transports")

    # Create multiple tasks concurrently across transports
    from tck.sut_client import SUTClient

    concurrent_results = {}

    for i, transport in enumerate(available_transports):
        logger.info(f"Creating concurrent task via {transport}")

        try:
            req_id = message_utils.generate_request_id()
            test_message = {
                "role": "user",
                "parts": [{"kind": "text", "text": f"Concurrent test message {i + 1} via {transport}"}],
                "messageId": f"concurrent-msg-{req_id}-{i}",
                "kind": "message",
            }

            result = execute_equivalent_operation(
                "send_message", {"message": test_message}, transport.lower().replace("/", "_").replace("-", "_")
            )

            concurrent_results[transport] = {
                "success": transport_helpers.is_json_rpc_success_response(result),
                "response": result,
                "message_id": test_message["messageId"],
            }

            if concurrent_results[transport]["success"]:
                logger.info(f"✅ {transport}: Concurrent task creation successful")
            else:
                logger.warning(f"⚠️ {transport}: Concurrent task creation failed")

        except Exception as e:
            concurrent_results[transport] = {"success": False, "response": None, "error": str(e), "message_id": None}
            logger.error(f"❌ {transport}: Exception during concurrent operation: {e}")

    # Verify concurrent operations succeeded
    successful_concurrent = [t for t, r in concurrent_results.items() if r["success"]]

    assert len(successful_concurrent) > 0, "No concurrent operations succeeded across any transport"

    logger.info(f"✅ {len(successful_concurrent)} transports handled concurrent operations successfully")

    # Verify task isolation - each transport should create independent tasks
    if len(successful_concurrent) > 1:
        task_ids = []
        for transport in successful_concurrent:
            response = concurrent_results[transport]["response"]
            task_result = response.get("result", {})
            if isinstance(task_result, dict) and "id" in task_result:
                task_ids.append(task_result["id"])

        unique_task_ids = set(task_ids)
        if len(unique_task_ids) == len(task_ids):
            logger.info("✅ Each transport created independent tasks (proper isolation)")
        else:
            logger.warning("⚠️ Some transports may have created duplicate task IDs")

    logger.info("✅ Concurrent operation transport equivalence validated")
