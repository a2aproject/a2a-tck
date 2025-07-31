"""
Base Transport Client for A2A Protocol v0.3.0

This module defines the abstract base class for all A2A transport implementations.
It provides a common interface that ensures functional equivalence across different
transport protocols (JSON-RPC 2.0, gRPC, HTTP+JSON/REST).

Specification Reference: A2A Protocol v0.3.0 §3.1 - Transport Layer Requirements
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class TransportType(Enum):
    """
    Enumeration of supported A2A transport protocols.
    
    Specification Reference: A2A Protocol v0.3.0 §3.2 - Supported Transport Protocols
    """
    JSON_RPC = "jsonrpc"
    GRPC = "grpc" 
    REST = "rest"


class TransportError(Exception):
    """
    Base exception class for transport-related errors.
    
    This exception provides a transport-agnostic way to handle errors
    that may occur during A2A protocol communication.
    """
    
    def __init__(self, message: str, transport_type: TransportType, 
                 original_error: Optional[Exception] = None):
        super().__init__(message)
        self.transport_type = transport_type
        self.original_error = original_error
        
    def __str__(self) -> str:
        base_msg = f"[{self.transport_type.value.upper()}] {super().__str__()}"
        if self.original_error:
            base_msg += f" (caused by: {self.original_error})"
        return base_msg


class BaseTransportClient(ABC):
    """
    Abstract base class for A2A transport client implementations.
    
    This class defines the common interface that all transport clients must implement
    to ensure functional equivalence across different A2A transport protocols.
    
    Specification Reference: A2A Protocol v0.3.0 §3.4.1 - Functional Equivalence Requirements
    """
    
    def __init__(self, base_url: str, transport_type: TransportType):
        """
        Initialize the transport client.
        
        Args:
            base_url: The base URL of the A2A server endpoint
            transport_type: The type of transport this client implements
        """
        self.base_url = base_url
        self.transport_type = transport_type
        self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
    @abstractmethod
    def send_message(self, message: Dict[str, Any], 
                    extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Send a message to the A2A server using the message/send method.
        
        This method implements the core A2A message sending functionality.
        All transport implementations must provide functionally equivalent behavior.
        
        Args:
            message: The message object conforming to A2A Message schema
            extra_headers: Optional transport-specific headers
            
        Returns:
            The response from the server containing task information
            
        Raises:
            TransportError: If the message sending fails
            
        Specification Reference: A2A Protocol v0.3.0 §7.1 - Core Message Protocol
        """
        pass
    
    @abstractmethod
    def send_streaming_message(self, message: Dict[str, Any],
                              extra_headers: Optional[Dict[str, str]] = None) -> Any:
        """
        Send a message with streaming response using message/stream method.
        
        This method implements streaming message functionality where the server
        provides real-time updates about task progress and results.
        
        Args:
            message: The message object conforming to A2A Message schema
            extra_headers: Optional transport-specific headers
            
        Returns:
            A stream object that yields task updates (transport-specific type)
            
        Raises:
            TransportError: If streaming message sending fails
            
        Specification Reference: A2A Protocol v0.3.0 §3.3 - Streaming Transport
        """
        pass
    
    @abstractmethod
    def get_task(self, task_id: str, history_length: Optional[int] = None,
                extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Get task status and information using tasks/get method.
        
        Args:
            task_id: The unique identifier of the task
            history_length: Optional number of historical state transitions to include
            extra_headers: Optional transport-specific headers
            
        Returns:
            The task object with current status and information
            
        Raises:
            TransportError: If task retrieval fails
            
        Specification Reference: A2A Protocol v0.3.0 §7.2 - Task Management
        """
        pass
    
    @abstractmethod 
    def cancel_task(self, task_id: str,
                   extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Cancel a task using tasks/cancel method.
        
        Args:
            task_id: The unique identifier of the task to cancel
            extra_headers: Optional transport-specific headers
            
        Returns:
            The response confirming task cancellation
            
        Raises:
            TransportError: If task cancellation fails
            
        Specification Reference: A2A Protocol v0.3.0 §7.2.2 - Task Cancellation
        """
        pass
    
    @abstractmethod
    def resubscribe_task(self, task_id: str,
                        extra_headers: Optional[Dict[str, str]] = None) -> Any:
        """
        Resubscribe to task updates using tasks/resubscribe method.
        
        This method allows resuming streaming updates for a task that was
        previously started but the stream was disconnected.
        
        Args:
            task_id: The unique identifier of the task to resubscribe to
            extra_headers: Optional transport-specific headers
            
        Returns:
            A stream object that yields task updates (transport-specific type)
            
        Raises:
            TransportError: If task resubscription fails
            
        Specification Reference: A2A Protocol v0.3.0 §7.2.4 - Task Resubscription
        """
        pass
    
    # Push notification configuration methods (v0.3.0 additions)
    
    @abstractmethod
    def set_push_notification_config(self, task_id: str, config: Dict[str, Any],
                                   extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Set push notification configuration for a task.
        
        Args:
            task_id: The unique identifier of the task
            config: Push notification configuration object
            extra_headers: Optional transport-specific headers
            
        Returns:
            The response confirming configuration was set
            
        Raises:
            TransportError: If configuration setting fails
            
        Specification Reference: A2A Protocol v0.3.0 §7.3 - Push Notifications
        """
        pass
    
    @abstractmethod
    def get_push_notification_config(self, task_id: str, config_id: str,
                                   extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Get push notification configuration for a task.
        
        Args:
            task_id: The unique identifier of the task
            config_id: The unique identifier of the configuration
            extra_headers: Optional transport-specific headers
            
        Returns:
            The push notification configuration object
            
        Raises:
            TransportError: If configuration retrieval fails
            
        Specification Reference: A2A Protocol v0.3.0 §7.3.2 - Get Push Notification Config
        """
        pass
    
    @abstractmethod
    def list_push_notification_configs(self, task_id: str,
                                     extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        List all push notification configurations for a task.
        
        Args:
            task_id: The unique identifier of the task
            extra_headers: Optional transport-specific headers
            
        Returns:
            List of push notification configurations
            
        Raises:
            TransportError: If configuration listing fails
            
        Specification Reference: A2A Protocol v0.3.0 §7.3.3 - List Push Notification Configs
        """
        pass
    
    @abstractmethod
    def delete_push_notification_config(self, task_id: str, config_id: str,
                                       extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Delete a push notification configuration for a task.
        
        Args:
            task_id: The unique identifier of the task
            config_id: The unique identifier of the configuration to delete
            extra_headers: Optional transport-specific headers
            
        Returns:
            The response confirming configuration was deleted
            
        Raises:
            TransportError: If configuration deletion fails
            
        Specification Reference: A2A Protocol v0.3.0 §7.3.4 - Delete Push Notification Config
        """
        pass
    
    # v0.3.0 new methods
    
    @abstractmethod
    def get_authenticated_extended_card(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Get the authenticated extended agent card.
        
        This method returns additional agent information that may only be available
        to authenticated clients.
        
        Args:
            extra_headers: Optional transport-specific headers (typically auth headers)
            
        Returns:
            The extended agent card with additional authenticated information
            
        Raises:
            TransportError: If authenticated card retrieval fails
            
        Specification Reference: A2A Protocol v0.3.0 §5.6 - Authenticated Extended Card
        """
        pass
    
    # Optional method for gRPC/REST only
    def list_tasks(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        List tasks (available in gRPC and REST transports only).
        
        This is an optional method that may not be available in all transport types.
        JSON-RPC transport does not support this method.
        
        Args:
            extra_headers: Optional transport-specific headers
            
        Returns:
            List of tasks
            
        Raises:
            TransportError: If task listing fails or is not supported
            NotImplementedError: If the transport doesn't support this method
            
        Specification Reference: A2A Protocol v0.3.0 §3.5.6 - Method Mapping Reference Table
        """
        raise NotImplementedError(f"list_tasks is not supported by {self.transport_type.value} transport")
    
    def supports_method(self, method_name: str) -> bool:
        """
        Check if this transport supports a specific method.
        
        Args:
            method_name: The name of the method to check
            
        Returns:
            True if the method is supported, False otherwise
        """
        # All transports support core methods
        core_methods = {
            "send_message", "send_streaming_message", "get_task", "cancel_task", 
            "resubscribe_task", "set_push_notification_config", 
            "get_push_notification_config", "list_push_notification_configs",
            "delete_push_notification_config", "get_authenticated_extended_card"
        }
        
        if method_name in core_methods:
            return True
            
        # Transport-specific methods
        if method_name == "list_tasks":
            return self.transport_type in [TransportType.GRPC, TransportType.REST]
            
        return False
    
    def get_transport_info(self) -> Dict[str, Any]:
        """
        Get information about this transport client.
        
        Returns:
            Dictionary containing transport metadata
        """
        return {
            "transport_type": self.transport_type.value,
            "base_url": self.base_url,
            "supported_methods": [
                method for method in [
                    "send_message", "send_streaming_message", "get_task", "cancel_task",
                    "resubscribe_task", "set_push_notification_config",
                    "get_push_notification_config", "list_push_notification_configs", 
                    "delete_push_notification_config", "get_authenticated_extended_card",
                    "list_tasks"
                ] if self.supports_method(method)
            ]
        }
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.transport_type.value}, {self.base_url})"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(base_url='{self.base_url}', transport_type={self.transport_type!r})"