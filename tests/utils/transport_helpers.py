"""
Transport-Agnostic Test Utilities for A2A v0.3.0

This module provides utility functions for migrating tests to work with any transport
while maintaining backward compatibility with existing JSON-RPC test patterns.

Specification Reference: A2A Protocol v0.3.0 §3.4.1 - Functional Equivalence Requirements
"""

import logging
from typing import Any, Dict, Optional, Union
import uuid

from tck import message_utils
from tck.transport.base_client import BaseTransportClient

logger = logging.getLogger(__name__)


def transport_send_message(client: BaseTransportClient, message_params: Dict[str, Any],
                          extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Send a message using any transport client, maintaining compatibility with existing tests.
    
    This function provides a transport-agnostic wrapper that works with both new
    BaseTransportClient implementations and legacy SUTClient patterns.
    
    Args:
        client: Transport client (BaseTransportClient or legacy SUTClient)
        message_params: Message parameters in A2A format
        extra_headers: Optional transport-specific headers
        
    Returns:
        Response from the server in JSON-RPC format for compatibility
        
    Specification Reference: A2A v0.3.0 §7.1 - Core Message Protocol
    """
    # Check if client is a BaseTransportClient with send_message method
    if hasattr(client, 'send_message') and hasattr(client, 'transport_type'):
        logger.debug(f"Using transport-aware send_message for {client.transport_type.value}")
        message = message_params.get("message", message_params)
        try:
            result = client.send_message(message, extra_headers)
            # Wrap result in JSON-RPC format for compatibility with existing tests
            return {"result": result}
        except Exception as e:
            # Convert transport exceptions to JSON-RPC error format
            logger.debug(f"Transport error: {e}")
            # Try to extract A2A error details from TransportError
            if hasattr(e, 'a2a_error') and e.a2a_error:
                return {"error": e.a2a_error}
            # Try to extract error details from legacy transport exception
            elif hasattr(e, 'json_rpc_error') and e.json_rpc_error:
                return {"error": e.json_rpc_error}
            return {"error": {"code": -32603, "message": str(e)}}
    
    # Fallback to legacy JSON-RPC pattern for backward compatibility
    elif hasattr(client, 'send_json_rpc'):
        logger.debug("Using legacy send_json_rpc for backward compatibility")
        req = message_utils.make_json_rpc_request("message/send", params=message_params)
        return client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    
    else:
        raise ValueError(f"Client {type(client)} does not support message sending")


def transport_get_task(client: BaseTransportClient, task_id: str, 
                      history_length: Optional[int] = None,
                      extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Get task status using any transport client.
    
    Args:
        client: Transport client
        task_id: Task identifier
        history_length: Optional history length parameter
        extra_headers: Optional transport-specific headers
        
    Returns:
        Task information from the server in JSON-RPC format for compatibility
        
    Specification Reference: A2A v0.3.0 §7.3 - Task Retrieval
    """
    # Check if client is a BaseTransportClient with get_task method
    if hasattr(client, 'get_task') and hasattr(client, 'transport_type'):
        logger.debug(f"Using transport-aware get_task for {client.transport_type.value}")
        try:
            result = client.get_task(task_id, history_length, extra_headers)
            # Wrap result in JSON-RPC format for compatibility with existing tests
            return {"result": result}
        except Exception as e:
            # Convert transport exceptions to JSON-RPC error format
            logger.debug(f"Transport error: {e}")
            # Try to extract A2A error details from TransportError
            if hasattr(e, 'a2a_error') and e.a2a_error:
                return {"error": e.a2a_error}
            # Try to extract error details from legacy transport exception
            elif hasattr(e, 'json_rpc_error') and e.json_rpc_error:
                return {"error": e.json_rpc_error}
            return {"error": {"code": -32603, "message": str(e)}}
    
    # Fallback to legacy JSON-RPC pattern
    elif hasattr(client, 'send_json_rpc'):
        logger.debug("Using legacy send_json_rpc for tasks/get")
        params = {"id": task_id}
        if history_length is not None:
            params["historyLength"] = history_length
        
        req = message_utils.make_json_rpc_request("tasks/get", params=params)
        return client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    
    else:
        raise ValueError(f"Client {type(client)} does not support task retrieval")


def transport_cancel_task(client: BaseTransportClient, task_id: str,
                         extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Cancel a task using any transport client.
    
    Args:
        client: Transport client
        task_id: Task identifier to cancel
        extra_headers: Optional transport-specific headers
        
    Returns:
        Cancellation response from the server in JSON-RPC format for compatibility
        
    Specification Reference: A2A v0.3.0 §7.4 - Task Cancellation
    """
    # Check if client is a BaseTransportClient with cancel_task method
    if hasattr(client, 'cancel_task') and hasattr(client, 'transport_type'):
        logger.debug(f"Using transport-aware cancel_task for {client.transport_type.value}")
        try:
            result = client.cancel_task(task_id, extra_headers)
            # Wrap result in JSON-RPC format for compatibility with existing tests
            return {"result": result}
        except Exception as e:
            # Convert transport exceptions to JSON-RPC error format
            logger.debug(f"Transport error: {e}")
            # Try to extract A2A error details from TransportError
            if hasattr(e, 'a2a_error') and e.a2a_error:
                return {"error": e.a2a_error}
            # Try to extract error details from legacy transport exception
            elif hasattr(e, 'json_rpc_error') and e.json_rpc_error:
                return {"error": e.json_rpc_error}
            return {"error": {"code": -32603, "message": str(e)}}
    
    # Fallback to legacy JSON-RPC pattern
    elif hasattr(client, 'send_json_rpc'):
        logger.debug("Using legacy send_json_rpc for tasks/cancel")
        params = {"id": task_id}
        req = message_utils.make_json_rpc_request("tasks/cancel", params=params)
        return client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    
    else:
        raise ValueError(f"Client {type(client)} does not support task cancellation")


def transport_get_agent_card(client: BaseTransportClient,
                           extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Get authenticated extended agent card using any transport client.
    
    Args:
        client: Transport client
        extra_headers: Optional transport-specific headers
        
    Returns:
        Agent card from the server in JSON-RPC format for compatibility
        
    Specification Reference: A2A v0.3.0 §9.1 - Authenticated Extended Agent Card
    """
    # Check if client is a BaseTransportClient with get_authenticated_extended_card method
    if hasattr(client, 'get_authenticated_extended_card') and hasattr(client, 'transport_type'):
        logger.debug(f"Using transport-aware get_authenticated_extended_card for {client.transport_type.value}")
        try:
            result = client.get_authenticated_extended_card(extra_headers)
            # Wrap result in JSON-RPC format for compatibility with existing tests
            return {"result": result}
        except Exception as e:
            # Convert transport exceptions to JSON-RPC error format
            logger.debug(f"Transport error: {e}")
            # Try to extract A2A error details from TransportError
            if hasattr(e, 'a2a_error') and e.a2a_error:
                return {"error": e.a2a_error}
            # Try to extract error details from legacy transport exception
            elif hasattr(e, 'json_rpc_error') and e.json_rpc_error:
                return {"error": e.json_rpc_error}
            return {"error": {"code": -32603, "message": str(e)}}
    
    # Fallback to legacy JSON-RPC pattern
    elif hasattr(client, 'send_json_rpc'):
        logger.debug("Using legacy send_json_rpc for agent/authenticatedExtendedCard")
        req = message_utils.make_json_rpc_request("agent/authenticatedExtendedCard", params={})
        return client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    
    else:
        raise ValueError(f"Client {type(client)} does not support agent card retrieval")


def is_json_rpc_success_response(response: Dict[str, Any], expected_id: Optional[str] = None) -> bool:
    """
    Check if a response is a successful JSON-RPC response.
    
    This function works with both transport-aware responses and legacy JSON-RPC responses.
    
    Args:
        response: Response to check
        expected_id: Expected request ID for JSON-RPC validation
        
    Returns:
        True if response indicates success
    """
    # Handle None responses
    if not response:
        return False
    
    # For full JSON-RPC responses, use the existing validation
    if "jsonrpc" in response and "id" in response:
        return message_utils.is_json_rpc_success_response(response, expected_id)
    
    # For transport-aware responses in JSON-RPC format ({"result": {...}} or {"error": {...}})
    if "error" in response:
        return False
    
    if "result" in response:
        return True
    
    # For direct task/message objects (legacy behavior)
    # If we have task-like structure, consider it successful
    if isinstance(response, dict) and ("id" in response or "status" in response or "kind" in response):
        return True
    
    # Default to False for unknown response formats
    return False


def is_json_rpc_error_response(response: Dict[str, Any], expected_error_code: Optional[int] = None) -> bool:
    """
    Check if a response is a JSON-RPC error response with optional error code validation.
    
    Args:
        response: Response to check
        expected_error_code: Expected error code (if any)
        
    Returns:
        True if response is an error response matching criteria
    """
    # Handle None responses
    if not response:
        return False
    
    # For all response types, check for error field
    if "error" in response:
        if expected_error_code is not None:
            return (response.get("error", {}).get("code") == expected_error_code)
        return True
    
    return False


def extract_task_id_from_response(response: Dict[str, Any]) -> Optional[str]:
    """
    Extract task ID from a transport response.
    
    This function works with both JSON-RPC and transport-aware response formats.
    
    Args:
        response: Response from any transport
        
    Returns:
        Task ID if found, None otherwise
    """
    # Handle None responses
    if not response:
        return None
    
    # For JSON-RPC responses, look in result
    if "result" in response:
        result = response["result"]
        if isinstance(result, dict) and "id" in result:
            return result["id"]
    
    # For direct task responses, look for id field
    if "id" in response:
        return response["id"]
    
    return None


def normalize_response_for_comparison(response: Dict[str, Any], transport_type: str) -> Dict[str, Any]:
    """
    Normalize a transport response for cross-transport comparison.
    
    This function standardizes responses from different transports to enable
    functional equivalence testing.
    
    Args:
        response: Response from transport
        transport_type: Type of transport ("jsonrpc", "grpc", "rest")
        
    Returns:
        Normalized response for comparison
        
    Specification Reference: A2A v0.3.0 §3.4.1 - Consistent Behavior
    """
    if not response:
        return {}
    
    normalized = {}
    
    # Handle responses with "result" wrapper (from transport helpers)
    if "result" in response:
        result = response["result"]
        normalized = result.copy() if isinstance(result, dict) else {"value": result}
    else:
        # Handle direct responses
        normalized = response.copy() if isinstance(response, dict) else {"value": response}
    
    # Remove transport-specific fields that shouldn't affect equivalence
    transport_specific_fields = [
        "jsonrpc", "id",  # JSON-RPC specific
        "_metadata", "_headers",  # gRPC/REST specific
        "requestId", "timestamp"  # Generic transport fields
    ]
    
    for field in transport_specific_fields:
        normalized.pop(field, None)
    
    return normalized


def generate_test_message_id(prefix: str = "test") -> str:
    """
    Generate a unique message ID for testing.
    
    Args:
        prefix: Prefix for the message ID
        
    Returns:
        Unique message ID string
    """
    return f"{prefix}-message-id-{uuid.uuid4()}"


def generate_test_task_id(prefix: str = "test") -> str:
    """
    Generate a unique task ID for testing.
    
    Args:
        prefix: Prefix for the task ID
        
    Returns:
        Unique task ID string
    """
    return f"{prefix}-task-id-{uuid.uuid4()}"


def is_transport_client(client: Any) -> bool:
    """
    Check if a client is a transport-aware BaseTransportClient.
    
    Args:
        client: Client to check
        
    Returns:
        True if client is a BaseTransportClient, False otherwise
    """
    return hasattr(client, 'transport_type') and hasattr(client, 'send_message')


def get_client_transport_type(client: Any) -> str:
    """
    Get the transport type of a client.
    
    Args:
        client: Transport client
        
    Returns:
        Transport type string ("jsonrpc", "grpc", "rest", or "unknown")
    """
    if hasattr(client, 'transport_type'):
        # Handle both enum and string transport types
        if hasattr(client.transport_type, 'value'):
            return client.transport_type.value.lower()
        else:
            return str(client.transport_type).lower()
    
    # Fallback detection based on class name or methods
    client_class_name = type(client).__name__.lower()
    if 'jsonrpc' in client_class_name or 'sut' in client_class_name:
        return "jsonrpc"
    elif 'grpc' in client_class_name:
        return "grpc"
    elif 'rest' in client_class_name or 'http' in client_class_name:
        return "rest"
    else:
        return "unknown"


def transport_send_json_rpc_request(client: BaseTransportClient, method: str, 
                                   params: Optional[Dict[str, Any]] = None,
                                   id: Optional[str] = None) -> Dict[str, Any]:
    """
    Send a raw JSON-RPC request using any transport client.
    
    This function sends arbitrary JSON-RPC methods that may not have dedicated
    transport helper functions yet.
    
    Args:
        client: Transport client
        method: JSON-RPC method name
        params: Optional method parameters
        id: Optional request ID
        
    Returns:
        JSON-RPC response from the server
        
    Specification Reference: A2A v0.3.0 §3.2.1 - JSON-RPC 2.0 Transport
    """
    # Create JSON-RPC request
    req = message_utils.make_json_rpc_request(method, params=params, id=id)
    
    # Check if client has raw JSON-RPC support (preferred for arbitrary methods)
    if hasattr(client, 'send_raw_json_rpc'):
        logger.debug(f"Using send_raw_json_rpc for method {method}")
        try:
            return client.send_raw_json_rpc(req)
        except Exception as e:
            # Handle transport-specific JSON-RPC error exceptions
            if hasattr(e, 'json_rpc_error') and e.json_rpc_error:
                # Return error in JSON-RPC format for consistency
                return {"error": e.json_rpc_error, "id": req.get("id")}
            raise
    
    # Fallback for other transport implementations
    else:
        raise ValueError(f"Client {type(client)} does not support arbitrary JSON-RPC requests")


def transport_set_push_notification_config(client: BaseTransportClient, task_id: str,
                                          config: Dict[str, Any],
                                          extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Set push notification configuration for a task using any transport client.
    
    Args:
        client: Transport client
        task_id: Task identifier
        config: Push notification configuration
        extra_headers: Optional transport-specific headers
        
    Returns:
        Response from the server in JSON-RPC format for compatibility
        
    Specification Reference: A2A v0.3.0 §7.5 - Push Notification Configuration
    """
    params = {
        "taskId": task_id,
        "pushNotificationConfig": config
    }
    
    return transport_send_json_rpc_request(client, "tasks/pushNotificationConfig/set", params)


def transport_get_push_notification_config(client: BaseTransportClient, task_id: str,
                                          extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Get push notification configuration for a task using any transport client.
    
    Args:
        client: Transport client
        task_id: Task identifier
        extra_headers: Optional transport-specific headers
        
    Returns:
        Response from the server in JSON-RPC format for compatibility
        
    Specification Reference: A2A v0.3.0 §7.6 - Push Notification Configuration
    """
    params = {"id": task_id}
    
    return transport_send_json_rpc_request(client, "tasks/pushNotificationConfig/get", params)


def transport_list_push_notification_configs(client: BaseTransportClient,
                                            extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    List all push notification configurations using any transport client.
    
    Args:
        client: Transport client
        extra_headers: Optional transport-specific headers
        
    Returns:
        Response from the server in JSON-RPC format for compatibility
        
    Specification Reference: A2A v0.3.0 §7.7 - Push Notification Configuration
    """
    return transport_send_json_rpc_request(client, "tasks/pushNotificationConfig/list", {})


def transport_delete_push_notification_config(client: BaseTransportClient, task_id: str,
                                             extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Delete push notification configuration for a task using any transport client.
    
    Args:
        client: Transport client
        task_id: Task identifier
        extra_headers: Optional transport-specific headers
        
    Returns:
        Response from the server in JSON-RPC format for compatibility
        
    Specification Reference: A2A v0.3.0 §7.8 - Push Notification Configuration
    """
    params = {"id": task_id}
    
    return transport_send_json_rpc_request(client, "tasks/pushNotificationConfig/delete", params)