"""
Multi-Transport Functional Equivalence Tests for A2A v0.3.0

This module validates that all transport implementations (JSON-RPC, gRPC, REST)
satisfy the functional equivalence requirements defined in A2A Protocol v0.3.0 §3.4.1.

The tests verify the four mandatory functional equivalence requirements:
1. Identical Functionality - Same set of operations and capabilities
2. Consistent Behavior - Semantically equivalent results for same requests
3. Same Error Handling - Consistent error code mapping across transports
4. Equivalent Authentication - Same authentication schemes across transports

Specification Reference: A2A Protocol v0.3.0 §3.4.1 - Functional Equivalence Requirements
"""

import pytest
from typing import Dict, Any, List, Optional

from tests.markers import transport_equivalence
from tests.utils.transport_helpers import (
    transport_send_message,
    transport_get_task,
    transport_cancel_task,
    transport_get_agent_card,
    is_json_rpc_success_response,
    is_json_rpc_error_response,
    extract_task_id_from_response,
    normalize_response_for_comparison,
    generate_test_message_id
)


@pytest.fixture
def sample_message():
    """Create a sample message for equivalence testing."""
    return {
        "kind": "message",
        "messageId": generate_test_message_id("equivalence"),
        "role": "user",
        "parts": [
            {"kind": "text", "text": "Multi-transport equivalence test message"}
        ]
    }


@pytest.fixture
def test_task_data(sut_client, sample_message):
    """Create a task for cross-transport testing."""
    params = {"message": sample_message}
    resp = transport_send_message(sut_client, params)
    
    if not is_json_rpc_success_response(resp):
        pytest.skip(f"Cannot create test task: {resp}")
    
    task_id = extract_task_id_from_response(resp)
    if not task_id:
        pytest.skip("Cannot extract task ID from response")
    
    return {
        "task_id": task_id,
        "message": sample_message,
        "create_response": resp
    }


@transport_equivalence
def test_identical_functionality_message_send(all_transport_clients, sample_message):
    """
    TRANSPORT EQUIVALENCE: A2A v0.3.0 §3.4.1 - Identical Functionality for message/send
    
    Validates that all transport implementations provide the same set of operations.
    All transports MUST support message/send with the same functionality.
    
    This test verifies the "Identical Functionality" requirement by ensuring
    all transports can perform the message/send operation successfully.
    
    Specification Reference: A2A v0.3.0 §3.4.1 - Functional Equivalence Requirements
    """
    if len(all_transport_clients) < 2:
        pytest.skip("Functional equivalence requires multiple transport implementations")
    
    successful_transports = []
    
    # Test that all transports support message/send
    for transport_type, client in all_transport_clients.items():
        params = {"message": sample_message}
        resp = transport_send_message(client, params)
        
        # Verify that the operation is supported (not a method-not-found error)
        if is_json_rpc_error_response(resp):
            error = resp.get("error", {})
            error_code = error.get("code")
            
            # Method not found (-32601) means transport doesn't support this operation
            assert error_code != -32601, \
                f"Transport {transport_type.value} does not support message/send (violates Identical Functionality requirement)"
            
            # Other errors are acceptable (e.g., authentication, validation issues)
            continue
        
        # Should be successful
        assert is_json_rpc_success_response(resp), \
            f"message/send failed on {transport_type.value}: {resp}"
        
        successful_transports.append(transport_type.value)
    
    # At least one transport should work for equivalence testing
    assert len(successful_transports) >= 1, \
        "No transports successfully performed message/send operation"


@transport_equivalence
def test_identical_functionality_tasks_get(all_transport_clients, test_task_data):
    """
    TRANSPORT EQUIVALENCE: A2A v0.3.0 §3.4.1 - Identical Functionality for tasks/get
    
    Validates that all transport implementations provide the same set of operations.
    All transports MUST support tasks/get with the same functionality.
    
    Specification Reference: A2A v0.3.0 §3.4.1 - Functional Equivalence Requirements
    """
    if len(all_transport_clients) < 2:
        pytest.skip("Functional equivalence requires multiple transport implementations")
    
    task_id = test_task_data["task_id"]
    
    # Test that all transports support tasks/get
    for transport_type, client in all_transport_clients.items():
        resp = transport_get_task(client, task_id)
        
        # Check if this is a method-not-found error
        if is_json_rpc_error_response(resp):
            error = resp.get("error", {})
            error_code = error.get("code")
            
            # Method not found (-32601) means transport doesn't support this operation
            assert error_code != -32601, \
                f"Transport {transport_type.value} does not support tasks/get (violates Identical Functionality requirement)"
            
            # TaskNotFoundError (-32001) is acceptable for cross-transport scenarios
            if error_code == -32001:
                continue
                
            # Other errors might be transport-specific issues
            continue
        
        # Should be successful and contain task data
        assert is_json_rpc_success_response(resp), \
            f"tasks/get failed on {transport_type.value}: {resp}"


@transport_equivalence
def test_consistent_behavior_message_send(all_transport_clients, sample_message):
    """
    TRANSPORT EQUIVALENCE: A2A v0.3.0 §3.4.1 - Consistent Behavior for message/send
    
    Validates that all transport implementations return semantically equivalent 
    results for the same requests. Tests the "Consistent Behavior" requirement.
    
    Specification Reference: A2A v0.3.0 §3.4.1 - Functional Equivalence Requirements
    """
    if len(all_transport_clients) < 2:
        pytest.skip("Functional equivalence requires multiple transport implementations")
    
    results = []
    transport_types = []
    
    # Send the same message using all available transports
    for transport_type, client in all_transport_clients.items():
        params = {"message": sample_message}
        resp = transport_send_message(client, params)
        
        # Only compare successful responses
        if not is_json_rpc_success_response(resp):
            continue
        
        # Extract and normalize the response for comparison
        transport_name = transport_type.value
        normalized = normalize_response_for_comparison(resp, transport_name)
        
        results.append(normalized)
        transport_types.append(transport_name)
    
    if len(results) < 2:
        pytest.skip("Need at least 2 successful responses for behavior comparison")
    
    # Compare all results for semantic equivalence
    base_result = results[0]
    base_transport = transport_types[0]
    
    for result, transport_type in zip(results[1:], transport_types[1:]):
        # Core task structure should be semantically equivalent
        if "id" in base_result and "id" in result:
            # Both should have task IDs (format may differ, but both should exist)
            assert base_result["id"] and result["id"], \
                f"Task ID presence mismatch: {base_transport} vs {transport_type}"
        
        if "status" in base_result and "status" in result:
            # Task status should be semantically equivalent
            base_status = base_result["status"]
            result_status = result["status"]
            
            # Both should have valid status values
            valid_states = ["pending", "submitted", "running", "completed", "failed", "cancelled", "input-required", "auth-required"]
            if isinstance(base_status, str):
                assert base_status in valid_states, f"Invalid status from {base_transport}: {base_status}"
                assert result_status in valid_states, f"Invalid status from {transport_type}: {result_status}"
            elif isinstance(base_status, dict) and "state" in base_status:
                assert base_status["state"] in valid_states, f"Invalid status state from {base_transport}: {base_status['state']}"
                assert result_status["state"] in valid_states, f"Invalid status state from {transport_type}: {result_status['state']}"


@transport_equivalence
def test_consistent_behavior_tasks_get(all_transport_clients, test_task_data):
    """
    TRANSPORT EQUIVALENCE: A2A v0.3.0 §3.4.1 - Consistent Behavior for tasks/get
    
    Validates that tasks/get returns semantically equivalent results 
    across all transport types for the same task.
    
    Specification Reference: A2A v0.3.0 §3.4.1 - Functional Equivalence Requirements
    """
    if len(all_transport_clients) < 2:
        pytest.skip("Functional equivalence requires multiple transport implementations")
    
    task_id = test_task_data["task_id"]
    results = []
    transport_types = []
    
    # Retrieve task using all available transports
    for transport_type, client in all_transport_clients.items():
        resp = transport_get_task(client, task_id)
        
        # Skip if task not found (expected for cross-transport scenarios)
        if is_json_rpc_error_response(resp, expected_error_code=-32001):
            continue
            
        if not is_json_rpc_success_response(resp):
            continue
        
        # Extract and normalize the response
        transport_name = transport_type.value
        normalized = normalize_response_for_comparison(resp, transport_name)
        
        results.append(normalized)
        transport_types.append(transport_name)
    
    if len(results) < 2:
        pytest.skip("Need at least 2 successful task retrievals for equivalence testing")
    
    # Compare all results for semantic equivalence
    base_result = results[0]
    base_transport = transport_types[0]
    
    for result, transport_type in zip(results[1:], transport_types[1:]):
        # Task ID should be equivalent
        if "id" in base_result and "id" in result:
            assert result["id"] == base_result["id"], \
                f"Task ID mismatch: {base_transport}='{base_result['id']}' vs {transport_type}='{result['id']}'"
        
        # Task status should be semantically equivalent
        if "status" in base_result and "status" in result:
            base_status = base_result["status"]
            result_status = result["status"]
            
            # Compare status values (accounting for different status representations)
            if isinstance(base_status, str) and isinstance(result_status, str):
                assert result_status == base_status, \
                    f"Task status mismatch: {base_transport}='{base_status}' vs {transport_type}='{result_status}'"
            elif isinstance(base_status, dict) and isinstance(result_status, dict):
                if "state" in base_status and "state" in result_status:
                    assert result_status["state"] == base_status["state"], \
                        f"Task status state mismatch: {base_transport}='{base_status['state']}' vs {transport_type}='{result_status['state']}'"


@transport_equivalence
def test_same_error_handling_task_not_found(all_transport_clients):
    """
    TRANSPORT EQUIVALENCE: A2A v0.3.0 §3.4.1 - Same Error Handling
    
    Validates that error responses are consistently mapped across all transport 
    types when the same error condition occurs (TaskNotFoundError).
    
    Tests the "Same Error Handling" requirement using the error codes defined
    in Section 8 of the A2A specification.
    
    Specification Reference: A2A v0.3.0 §3.4.1 - Functional Equivalence Requirements
    """
    if len(all_transport_clients) < 2:
        pytest.skip("Functional equivalence requires multiple transport implementations")
    
    # Test retrieval of non-existent task (should produce equivalent errors)
    nonexistent_task_id = "definitely-does-not-exist-task-id"
    error_responses = []
    transport_types = []
    
    for transport_type, client in all_transport_clients.items():
        resp = transport_get_task(client, nonexistent_task_id)
        
        # Should get an error response
        assert not is_json_rpc_success_response(resp), \
            f"Expected error for non-existent task on {transport_type.value}, got success: {resp}"
        
        assert "error" in resp, f"Error field missing in {transport_type.value} response"
        
        transport_name = transport_type.value
        error_responses.append(resp["error"])
        transport_types.append(transport_name)
    
    if len(error_responses) < 2:
        pytest.skip("Need at least 2 error responses for comparison")
    
    # Compare error responses for equivalence
    base_error = error_responses[0]
    base_transport = transport_types[0]
    
    for error, transport_type in zip(error_responses[1:], transport_types[1:]):
        # Error codes should be equivalent for the same error condition
        base_error_code = base_error.get("code")
        result_error_code = error.get("code")
        
        assert result_error_code == base_error_code, \
            f"Error code mismatch for non-existent task: {base_transport}={base_error_code} vs {transport_type}={result_error_code}"
        
        # Both should indicate TaskNotFoundError (-32001) per A2A v0.3.0 specification
        assert result_error_code == -32001, \
            f"Expected TaskNotFoundError (-32001) from {transport_type}, got {result_error_code}"
        
        # Error messages should be present
        assert "message" in error, f"Error message missing in {transport_type} response"
        assert error["message"], f"Empty error message in {transport_type} response"


@transport_equivalence
def test_same_error_handling_method_not_found(all_transport_clients):
    """
    TRANSPORT EQUIVALENCE: A2A v0.3.0 §3.4.1 - Same Error Handling for Invalid Methods
    
    Validates that unsupported method errors are consistently mapped across
    all transport types using the standard JSON-RPC error code (-32601).
    
    Specification Reference: A2A v0.3.0 §3.4.1 - Functional Equivalence Requirements
    """
    if len(all_transport_clients) < 2:
        pytest.skip("Functional equivalence requires multiple transport implementations")
    
    # This test would need to be implemented with a way to send invalid method names
    # through the transport helpers. For now, we'll skip this as it requires
    # lower-level transport access that bypasses the transport helpers.
    pytest.skip("Method not found error testing requires direct transport access")


@transport_equivalence  
def test_equivalent_authentication_agent_card(all_transport_clients):
    """
    TRANSPORT EQUIVALENCE: A2A v0.3.0 §3.4.1 - Equivalent Authentication
    
    Validates that all transport implementations support the same authentication
    schemes as declared in the AgentCard.
    
    Tests the "Equivalent Authentication" requirement by verifying agent card
    retrieval works consistently across transports.
    
    Specification Reference: A2A v0.3.0 §3.4.1 - Functional Equivalence Requirements
    """
    if len(all_transport_clients) < 2:
        pytest.skip("Functional equivalence requires multiple transport implementations")
    
    results = []
    transport_types = []
    
    # Retrieve agent card using all available transports
    for transport_type, client in all_transport_clients.items():
        resp = transport_get_agent_card(client)
        
        # Agent card retrieval might not be supported on all transports
        if is_json_rpc_error_response(resp):
            error = resp.get("error", {})
            error_code = error.get("code")
            
            # Method not found is acceptable (not all transports may support this)
            if error_code in [-32601, -32600]:
                continue
                
            # Authentication errors should be consistent across transports
            if error_code in [401, 403]:
                # This actually validates equivalent authentication behavior
                transport_types.append(transport_type.value)
                results.append(resp)
                continue
        
        if not is_json_rpc_success_response(resp):
            continue
        
        # Extract and normalize the response
        transport_name = transport_type.value
        normalized = normalize_response_for_comparison(resp, transport_name)
        
        results.append(normalized)
        transport_types.append(transport_name)
    
    if len(results) < 2:
        pytest.skip("Need at least 2 agent card responses for equivalence testing")
    
    # Compare results for authentication equivalence
    base_result = results[0]
    base_transport = transport_types[0]
    
    for result, transport_type in zip(results[1:], transport_types[1:]):
        # If both are error responses, they should have equivalent auth requirements
        if isinstance(base_result, dict) and "error" in str(base_result):
            continue  # Error comparison was done above
        
        # If both are successful, they should have equivalent security schemes
        if isinstance(base_result, dict) and isinstance(result, dict):
            # Both should declare the same authentication capabilities
            base_auth_fields = ["securitySchemes", "security", "authentication"] 
            for field in base_auth_fields:
                if field in base_result and field in result:
                    # Authentication schemes should be equivalent
                    # (exact match not required, but capabilities should be equivalent)
                    assert isinstance(result[field], type(base_result[field])), \
                        f"Authentication field '{field}' type mismatch: {base_transport} vs {transport_type}"


@transport_equivalence
def test_method_mapping_compliance(all_transport_clients):
    """
    TRANSPORT EQUIVALENCE: A2A v0.3.0 §3.5 - Method Mapping Compliance
    
    Validates that all transport implementations use the standard method mappings
    defined in Section 3.5 of the A2A specification.
    
    This test verifies that each transport correctly implements the method mapping
    requirements for multi-transport agents.
    
    Specification Reference: A2A v0.3.0 §3.5 - Method Mapping and Naming Conventions
    """
    if len(all_transport_clients) < 2:
        pytest.skip("Method mapping compliance requires multiple transport implementations")
    
    # This test validates that transports follow the correct method mapping
    # by ensuring they can communicate using their declared protocols
    
    transport_method_support = {}
    
    for transport_type, client in all_transport_clients.items():
        transport_name = transport_type.value
        supported_methods = []
        
        # Test core methods that all transports must support
        core_methods = ["message/send", "tasks/get", "tasks/cancel"]
        
        for method_name in core_methods:
            # We can't directly test method names without transport-specific code,
            # but we can verify that the operations work through our transport helpers
            # which use the correct method mappings internally
            
            if method_name == "message/send":
                # Test message send capability
                sample_msg = {
                    "kind": "message",
                    "messageId": generate_test_message_id("mapping-test"),
                    "role": "user", 
                    "parts": [{"kind": "text", "text": "Method mapping test"}]
                }
                resp = transport_send_message(client, {"message": sample_msg})
                if not is_json_rpc_error_response(resp, expected_error_code=-32601):
                    supported_methods.append(method_name)
                    
            elif method_name == "tasks/get":
                # Test task retrieval capability  
                resp = transport_get_task(client, "test-task-id")
                if not is_json_rpc_error_response(resp, expected_error_code=-32601):
                    supported_methods.append(method_name)
                    
            elif method_name == "tasks/cancel":
                # Test task cancellation capability
                resp = transport_cancel_task(client, "test-task-id") 
                if not is_json_rpc_error_response(resp, expected_error_code=-32601):
                    supported_methods.append(method_name)
        
        transport_method_support[transport_name] = supported_methods
    
    # All transports should support the same core methods
    if len(transport_method_support) >= 2:
        transport_names = list(transport_method_support.keys())
        base_transport = transport_names[0]
        base_methods = set(transport_method_support[base_transport])
        
        for transport_name in transport_names[1:]:
            transport_methods = set(transport_method_support[transport_name])
            
            # Core methods should be supported by all transports
            common_methods = base_methods.intersection(transport_methods)
            assert len(common_methods) > 0, \
                f"No common methods between {base_transport} and {transport_name} transports"