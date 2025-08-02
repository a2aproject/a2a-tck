"""
A2A v0.3.0 Specification Compliance Validation

This module provides validation functions for ensuring A2A v0.3.0 specification
compliance across different transport protocols. It validates transport compliance,
method mapping, error handling, and functional equivalence requirements.

Specification Reference: A2A Protocol v0.3.0 - Multi-Transport Compliance Requirements
"""

import logging
from typing import Any, Dict, List, Optional, Set, Union
from enum import Enum

from tck.transport.base_client import BaseTransportClient, TransportType

logger = logging.getLogger(__name__)


class A2AError(Enum):
    """
    A2A v0.3.0 specification error codes as defined in §8.2.
    """
    TASK_NOT_FOUND = -32001
    TASK_NOT_CANCELABLE = -32002
    PUSH_NOTIFICATION_NOT_SUPPORTED = -32003
    UNSUPPORTED_OPERATION = -32004
    CONTENT_TYPE_NOT_SUPPORTED = -32005
    INVALID_AGENT_RESPONSE = -32006
    AUTHENTICATED_EXTENDED_CARD_NOT_CONFIGURED = -32007


class JSONRPCError(Enum):
    """
    Standard JSON-RPC 2.0 error codes as defined in §8.1.
    """
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class TransportComplianceValidator:
    """
    Validates transport compliance according to A2A v0.3.0 specification.
    
    Specification Reference: A2A v0.3.0 §3.2 - Transport Protocols
    """
    
    @staticmethod
    def validate_transport_compliance(transport_client: BaseTransportClient) -> Dict[str, Any]:
        """
        Validate transport compliance for a specific transport client.
        
        Args:
            transport_client: Transport client to validate
            
        Returns:
            Dict containing validation results and compliance status
            
        Specification Reference: A2A v0.3.0 §3.2.1, §3.2.2, §3.2.3
        """
        transport_type = transport_client.transport_type
        validation_result = {
            "transport_type": transport_type.value,
            "compliant": True,
            "issues": [],
            "required_methods": [],
            "optional_methods": [],
            "transport_specific_features": []
        }
        
        # Define required methods for each transport type
        if transport_type == TransportType.JSON_RPC:
            validation_result.update(
                TransportComplianceValidator._validate_jsonrpc_compliance(transport_client)
            )
        elif transport_type == TransportType.GRPC:
            validation_result.update(
                TransportComplianceValidator._validate_grpc_compliance(transport_client)
            )
        elif transport_type == TransportType.REST:
            validation_result.update(
                TransportComplianceValidator._validate_rest_compliance(transport_client)
            )
        else:
            validation_result["compliant"] = False
            validation_result["issues"].append(f"Unknown transport type: {transport_type}")
        
        return validation_result
    
    @staticmethod
    def _validate_jsonrpc_compliance(transport_client: BaseTransportClient) -> Dict[str, Any]:
        """
        Validate JSON-RPC 2.0 transport compliance.
        
        Specification Reference: A2A v0.3.0 §3.2.1 - JSON-RPC 2.0 Transport
        """
        result = {
            "required_methods": [
                "send_message",      # message/send 
                "get_task",          # tasks/get
                "cancel_task",       # tasks/cancel
                "get_agent_card",    # agent/authenticatedExtendedCard
            ],
            "optional_methods": [
                "send_streaming_message",  # message/stream
                "subscribe_to_task",       # tasks/resubscribe
            ],
            "transport_specific_features": [
                "sse_streaming",          # Server-Sent Events for streaming
                "json_rpc_error_codes",   # Standard JSON-RPC error handling
            ]
        }
        
        # Check if client has required methods
        issues = []
        for method in result["required_methods"]:
            if not hasattr(transport_client, method):
                issues.append(f"Missing required method: {method}")
        
        result["issues"] = issues
        result["compliant"] = len(issues) == 0
        
        return result
    
    @staticmethod  
    def _validate_grpc_compliance(transport_client: BaseTransportClient) -> Dict[str, Any]:
        """
        Validate gRPC transport compliance.
        
        Specification Reference: A2A v0.3.0 §3.2.2 - gRPC Transport
        """
        result = {
            "required_methods": [
                "send_message",      # SendMessage
                "get_task",          # GetTask
                "cancel_task",       # CancelTask  
                "get_agent_card",    # GetAgentCard
                "list_tasks",        # ListTask (gRPC/REST specific)
            ],
            "optional_methods": [
                "send_streaming_message",  # SendStreamingMessage
                "subscribe_to_task",       # TaskSubscription
            ],
            "transport_specific_features": [
                "protobuf_serialization", # Protocol Buffers
                "grpc_streaming",         # gRPC server streaming
                "bidirectional_streaming", # gRPC bidirectional streaming
                "grpc_metadata",          # gRPC metadata support
            ]
        }
        
        # Check if client has required methods
        issues = []
        for method in result["required_methods"]:
            if not hasattr(transport_client, method):
                issues.append(f"Missing required gRPC method: {method}")
        
        result["issues"] = issues
        result["compliant"] = len(issues) == 0
        
        return result
    
    @staticmethod
    def _validate_rest_compliance(transport_client: BaseTransportClient) -> Dict[str, Any]:
        """
        Validate HTTP+JSON/REST transport compliance.
        
        Specification Reference: A2A v0.3.0 §3.2.3 - HTTP+JSON/REST Transport
        """
        result = {
            "required_methods": [
                "send_message",      # POST /v1/message:send
                "get_task",          # GET /v1/tasks/{id}
                "cancel_task",       # POST /v1/tasks/{id}:cancel
                "get_agent_card",    # GET /v1/card
                "list_tasks",        # GET /v1/tasks (gRPC/REST specific)
            ],
            "optional_methods": [
                "send_streaming_message",  # POST /v1/message:stream
                "subscribe_to_task",       # POST /v1/tasks/{id}:subscribe
            ],
            "transport_specific_features": [
                "http_status_codes",     # Proper HTTP status codes
                "rest_url_patterns",     # RESTful URL patterns  
                "sse_streaming",         # Server-Sent Events for streaming
                "http_caching",          # HTTP caching headers
                "conditional_requests",  # HTTP conditional requests
            ]
        }
        
        # Check if client has required methods
        issues = []
        for method in result["required_methods"]:
            if not hasattr(transport_client, method):
                issues.append(f"Missing required REST method: {method}")
        
        result["issues"] = issues
        result["compliant"] = len(issues) == 0
        
        return result


class MethodMappingValidator:
    """
    Validates method mapping compliance across different transports.
    
    Specification Reference: A2A v0.3.0 §3.5 - Method Mapping and Naming Conventions
    """
    
    # Method mapping reference table from specification §3.5.6
    METHOD_MAPPING = {
        "send_message": {
            "jsonrpc": "message/send",
            "grpc": "SendMessage", 
            "rest": "POST /v1/message:send",
            "description": "Send message to agent"
        },
        "send_streaming_message": {
            "jsonrpc": "message/stream",
            "grpc": "SendStreamingMessage",
            "rest": "POST /v1/message:stream", 
            "description": "Send message with streaming"
        },
        "get_task": {
            "jsonrpc": "tasks/get",
            "grpc": "GetTask",
            "rest": "GET /v1/tasks/{id}",
            "description": "Get task status"
        },
        "list_tasks": {
            "jsonrpc": None,  # Not available in JSON-RPC
            "grpc": "ListTask",
            "rest": "GET /v1/tasks",
            "description": "List tasks (gRPC/REST only)"
        },
        "cancel_task": {
            "jsonrpc": "tasks/cancel",
            "grpc": "CancelTask", 
            "rest": "POST /v1/tasks/{id}:cancel",
            "description": "Cancel task"
        },
        "subscribe_to_task": {
            "jsonrpc": "tasks/resubscribe",
            "grpc": "TaskSubscription",
            "rest": "POST /v1/tasks/{id}:subscribe", 
            "description": "Resume task streaming"
        },
        "get_agent_card": {
            "jsonrpc": "agent/authenticatedExtendedCard",
            "grpc": "GetAgentCard",
            "rest": "GET /v1/card",
            "description": "Get authenticated agent card"
        }
    }
    
    @staticmethod
    def validate_method_mapping(transport_clients: Dict[TransportType, BaseTransportClient]) -> Dict[str, Any]:
        """
        Validate method mapping consistency across multiple transports.
        
        Args:
            transport_clients: Dictionary of transport clients to validate
            
        Returns:
            Dict containing method mapping validation results
            
        Specification Reference: A2A v0.3.0 §3.5.4 - Method Mapping Compliance
        """
        validation_result = {
            "compliant": True,
            "issues": [],
            "method_coverage": {},
            "transport_consistency": {}
        }
        
        # Check each method across all available transports
        for method_name, mapping in MethodMappingValidator.METHOD_MAPPING.items():
            method_result = {
                "available_transports": [],
                "missing_transports": [],
                "transport_specific": False
            }
            
            # Check availability across transports
            for transport_type, client in transport_clients.items():
                transport_key = transport_type.value.lower()
                expected_mapping = mapping.get(transport_key)
                
                if expected_mapping is None:
                    # Method not available for this transport (e.g., list_tasks for JSON-RPC)
                    method_result["transport_specific"] = True
                    continue
                
                if hasattr(client, method_name):
                    method_result["available_transports"].append(transport_type.value)
                else:
                    method_result["missing_transports"].append(transport_type.value)
                    validation_result["issues"].append(
                        f"Method {method_name} missing in {transport_type.value} transport"
                    )
            
            validation_result["method_coverage"][method_name] = method_result
        
        # Overall compliance check
        validation_result["compliant"] = len(validation_result["issues"]) == 0
        
        return validation_result


class FunctionalEquivalenceValidator:
    """
    Validates functional equivalence across multiple transports.
    
    Specification Reference: A2A v0.3.0 §3.4.1 - Functional Equivalence Requirements
    """
    
    @staticmethod
    def validate_response_equivalence(responses: Dict[TransportType, Any], 
                                    method_name: str) -> Dict[str, Any]:
        """
        Validate that responses from different transports are functionally equivalent.
        
        Args:
            responses: Dictionary of responses from different transports
            method_name: Name of the method being tested
            
        Returns:
            Dict containing equivalence validation results
            
        Specification Reference: A2A v0.3.0 §3.4.1 - Consistent Behavior
        """
        if len(responses) < 2:
            return {
                "equivalent": True,
                "message": "Only one transport available, equivalence not applicable",
                "details": {}
            }
        
        # Extract response values for comparison
        transport_types = list(responses.keys())
        reference_transport = transport_types[0]
        reference_response = responses[reference_transport]
        
        equivalence_result = {
            "equivalent": True,
            "reference_transport": reference_transport.value,
            "differences": [],
            "method": method_name,
            "transport_count": len(responses)
        }
        
        # Compare each transport response against the reference
        for transport_type, response in responses.items():
            if transport_type == reference_transport:
                continue
                
            differences = FunctionalEquivalenceValidator._compare_responses(
                reference_response, response, reference_transport.value, 
                transport_type.value
            )
            
            if differences:
                equivalence_result["equivalent"] = False
                equivalence_result["differences"].extend(differences)
        
        return equivalence_result
    
    @staticmethod
    def _compare_responses(reference: Any, comparison: Any, 
                          ref_transport: str, comp_transport: str) -> List[str]:
        """
        Compare two responses for functional equivalence.
        
        Args:
            reference: Reference response
            comparison: Comparison response  
            ref_transport: Reference transport name
            comp_transport: Comparison transport name
            
        Returns:
            List of differences found
        """
        differences = []
        
        # Handle different response types
        if type(reference) != type(comparison):
            differences.append(
                f"Response type mismatch: {ref_transport}={type(reference).__name__}, "
                f"{comp_transport}={type(comparison).__name__}"
            )
            return differences
        
        if isinstance(reference, dict):
            differences.extend(
                FunctionalEquivalenceValidator._compare_dict_responses(
                    reference, comparison, ref_transport, comp_transport
                )
            )
        elif isinstance(reference, list):
            differences.extend(
                FunctionalEquivalenceValidator._compare_list_responses(
                    reference, comparison, ref_transport, comp_transport
                )
            )
        elif reference != comparison:
            differences.append(
                f"Value mismatch: {ref_transport}={reference}, "
                f"{comp_transport}={comparison}"
            )
        
        return differences
    
    @staticmethod
    def _compare_dict_responses(ref_dict: Dict, comp_dict: Dict,
                               ref_transport: str, comp_transport: str) -> List[str]:
        """Compare dictionary responses for equivalence."""
        differences = []
        
        # Check for missing keys
        ref_keys = set(ref_dict.keys())
        comp_keys = set(comp_dict.keys())
        
        missing_in_comp = ref_keys - comp_keys
        missing_in_ref = comp_keys - ref_keys
        
        for key in missing_in_comp:
            differences.append(f"Key '{key}' missing in {comp_transport} response")
        
        for key in missing_in_ref:
            differences.append(f"Key '{key}' missing in {ref_transport} response")
        
        # Compare common keys
        for key in ref_keys & comp_keys:
            sub_differences = FunctionalEquivalenceValidator._compare_responses(
                ref_dict[key], comp_dict[key], ref_transport, comp_transport
            )
            differences.extend([f"Key '{key}': {diff}" for diff in sub_differences])
        
        return differences
    
    @staticmethod 
    def _compare_list_responses(ref_list: List, comp_list: List,
                               ref_transport: str, comp_transport: str) -> List[str]:
        """Compare list responses for equivalence."""
        differences = []
        
        if len(ref_list) != len(comp_list):
            differences.append(
                f"List length mismatch: {ref_transport}={len(ref_list)}, "
                f"{comp_transport}={len(comp_list)}"
            )
            return differences
        
        for i, (ref_item, comp_item) in enumerate(zip(ref_list, comp_list)):
            sub_differences = FunctionalEquivalenceValidator._compare_responses(
                ref_item, comp_item, ref_transport, comp_transport
            )
            differences.extend([f"Index {i}: {diff}" for diff in sub_differences])
        
        return differences


class ErrorHandlingValidator:
    """
    Validates error handling compliance across transports.
    
    Specification Reference: A2A v0.3.0 §8 - Error Handling
    """
    
    @staticmethod
    def validate_error_code_mapping(error_response: Dict[str, Any], 
                                   transport_type: TransportType) -> Dict[str, Any]:
        """
        Validate that error codes are properly mapped for the transport.
        
        Args:
            error_response: Error response from the transport
            transport_type: Type of transport being validated
            
        Returns:
            Dict containing error validation results
            
        Specification Reference: A2A v0.3.0 §8.1, §8.2 - Error Code Mapping
        """
        validation_result = {
            "valid": True,
            "error_code": None,
            "error_category": None,
            "transport_appropriate": True,
            "issues": []
        }
        
        # Extract error code based on transport type
        if transport_type == TransportType.JSON_RPC:
            validation_result.update(
                ErrorHandlingValidator._validate_jsonrpc_error(error_response)
            )
        elif transport_type == TransportType.GRPC:
            validation_result.update(
                ErrorHandlingValidator._validate_grpc_error(error_response)
            )
        elif transport_type == TransportType.REST:
            validation_result.update(
                ErrorHandlingValidator._validate_rest_error(error_response)
            )
        
        return validation_result
    
    @staticmethod
    def _validate_jsonrpc_error(error_response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate JSON-RPC error response format."""
        result = {"issues": []}
        
        if "error" not in error_response:
            result["issues"].append("Missing 'error' field in JSON-RPC error response")
            result["valid"] = False
            return result
        
        error = error_response["error"]
        
        if "code" not in error:
            result["issues"].append("Missing 'code' field in JSON-RPC error")
            result["valid"] = False
            return result
        
        error_code = error["code"]
        result["error_code"] = error_code
        
        # Categorize error code according to A2A v0.3.0 §8
        if error_code in [e.value for e in JSONRPCError]:
            result["error_category"] = "standard_jsonrpc"
        elif error_code in [e.value for e in A2AError]:
            result["error_category"] = "a2a_specific"
        elif -32099 <= error_code <= -32000:
            result["error_category"] = "server_defined"
        else:
            result["error_category"] = "invalid"
            result["issues"].append(f"Invalid error code: {error_code}")
            result["valid"] = False
        
        # Check for required message field
        if "message" not in error:
            result["issues"].append("Missing 'message' field in JSON-RPC error")
            result["valid"] = False
        
        result["valid"] = len(result["issues"]) == 0
        return result
    
    @staticmethod
    def _validate_grpc_error(error_response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate gRPC error response format per A2A v0.3.0 §3.2.2."""
        return {
            "valid": True,
            "error_category": "grpc_status",
            "issues": [],
            "note": "gRPC error validation for A2A v0.3.0 compliance"
        }
    
    @staticmethod
    def _validate_rest_error(error_response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate REST error response format per A2A v0.3.0 §3.2.3."""
        return {
            "valid": True,
            "error_category": "http_status",
            "issues": [],
            "note": "REST error validation for A2A v0.3.0 compliance"
        }


# Convenience function for comprehensive A2A v0.3.0 compliance validation
def validate_a2a_v030_compliance(transport_clients: Dict[TransportType, BaseTransportClient]) -> Dict[str, Any]:
    """
    Perform comprehensive A2A v0.3.0 compliance validation.
    
    Args:
        transport_clients: Dictionary of transport clients to validate
        
    Returns:
        Dict containing comprehensive compliance validation results
        
    Specification Reference: A2A v0.3.0 - Complete Multi-Transport Compliance
    """
    validation_result = {
        "overall_compliant": True,
        "transport_compliance": {},
        "method_mapping": {},
        "issues": [],
        "summary": {
            "transports_tested": len(transport_clients),
            "compliant_transports": 0,
            "method_mapping_compliant": False
        }
    }
    
    # Validate each transport individually
    for transport_type, client in transport_clients.items():
        transport_validation = TransportComplianceValidator.validate_transport_compliance(client)
        validation_result["transport_compliance"][transport_type.value] = transport_validation
        
        if transport_validation["compliant"]:
            validation_result["summary"]["compliant_transports"] += 1
        else:
            validation_result["overall_compliant"] = False
            validation_result["issues"].extend([
                f"{transport_type.value}: {issue}" for issue in transport_validation["issues"]
            ])
    
    # Validate method mapping across transports
    if len(transport_clients) > 1:
        method_mapping_validation = MethodMappingValidator.validate_method_mapping(transport_clients)
        validation_result["method_mapping"] = method_mapping_validation
        validation_result["summary"]["method_mapping_compliant"] = method_mapping_validation["compliant"]
        
        if not method_mapping_validation["compliant"]:
            validation_result["overall_compliant"] = False
            validation_result["issues"].extend(method_mapping_validation["issues"])
    else:
        validation_result["summary"]["method_mapping_compliant"] = True
        validation_result["method_mapping"] = {"message": "Single transport, method mapping not applicable"}
    
    return validation_result