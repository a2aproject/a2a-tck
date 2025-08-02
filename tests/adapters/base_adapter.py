"""
Base Transport Adapter for A2A Protocol v0.3.0 TCK Testing

This module provides the abstract base class for transport-specific test adapters.
It enables transport-agnostic test patterns while maintaining real network communication
with live SUTs for compliance verification.

The adapter framework ensures that the same test logic can be executed against
different A2A transport protocols without mocking, providing true protocol compliance
validation through real network interactions.

Specification Reference: A2A Protocol v0.3.0 §3.4 - Transport Compliance Testing
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Iterator, Callable
from datetime import datetime, timezone

from tck.transport.base_client import BaseTransportClient, TransportType, TransportError

logger = logging.getLogger(__name__)


class TestOutcome(Enum):
    """Test execution outcomes."""
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class TestContext:
    """
    Context information for transport-agnostic test execution.
    
    This class encapsulates all the information needed to execute a test
    against any A2A transport protocol while maintaining real SUT communication.
    """
    transport_type: TransportType
    sut_endpoint: str
    test_name: str
    spec_reference: Optional[str] = None
    extra_headers: Optional[Dict[str, str]] = field(default_factory=dict)
    timeout: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize context with current timestamp."""
        if 'start_time' not in self.metadata:
            self.metadata['start_time'] = datetime.now(timezone.utc)


@dataclass 
class TestResult:
    """
    Result of a transport-agnostic test execution.
    
    Captures the outcome, timing, and detailed information from real SUT testing
    across any A2A transport protocol.
    """
    outcome: TestOutcome
    test_name: str
    transport_type: TransportType
    spec_reference: Optional[str] = None
    duration_ms: Optional[float] = None
    sut_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    assertions_passed: int = 0
    assertions_total: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate assertion success rate."""
        if self.assertions_total == 0:
            return 1.0 if self.outcome == TestOutcome.PASS else 0.0
        return self.assertions_passed / self.assertions_total
    
    def __str__(self) -> str:
        status = f"{self.outcome.value.upper()}"
        if self.duration_ms:
            status += f" ({self.duration_ms:.1f}ms)"
        if self.assertions_total > 0:
            status += f" [{self.assertions_passed}/{self.assertions_total} assertions]"
        return f"{self.test_name} [{self.transport_type.value}]: {status}"


class BaseTransportAdapter(ABC):
    """
    Abstract base class for transport-specific test adapters.
    
    This class provides the framework for implementing transport-agnostic tests
    that execute against real SUTs across different A2A protocol transports.
    
    Each transport adapter implements this interface to provide protocol-specific
    communication while maintaining consistent test patterns and assertions.
    
    Specification Reference: A2A Protocol v0.3.0 §3.4.1 - Functional Equivalence Requirements
    """
    
    def __init__(self, transport_client: BaseTransportClient):
        """
        Initialize the transport adapter.
        
        Args:
            transport_client: Real transport client for SUT communication
        """
        self.transport_client = transport_client
        self.transport_type = transport_client.transport_type
        self.sut_endpoint = transport_client.base_url
        self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        self._logger.info(f"Initialized {self.transport_type.value} adapter for {self.sut_endpoint}")
    
    # Core A2A Protocol Test Methods (Real SUT Communication)
    
    @abstractmethod
    def test_send_message(self, context: TestContext, message: Dict[str, Any]) -> TestResult:
        """
        Test message/send method with real SUT communication.
        
        This method executes a real message/send call against the live SUT
        to validate protocol compliance for message handling.
        
        Args:
            context: Test execution context
            message: A2A message object to send
            
        Returns:
            TestResult with outcome from real SUT interaction
            
        Specification Reference: A2A Protocol v0.3.0 §7.1 - Core Message Protocol
        """
        pass
    
    @abstractmethod
    def test_send_streaming_message(self, context: TestContext, message: Dict[str, Any]) -> TestResult:
        """
        Test message/stream method with real SUT streaming communication.
        
        This method executes a real streaming message call against the live SUT
        to validate streaming protocol compliance.
        
        Args:
            context: Test execution context
            message: A2A message object for streaming
            
        Returns:
            TestResult with outcome from real SUT streaming interaction
            
        Specification Reference: A2A Protocol v0.3.0 §3.3 - Streaming Transport
        """
        pass
    
    @abstractmethod
    def test_get_task(self, context: TestContext, task_id: str, 
                     history_length: Optional[int] = None) -> TestResult:
        """
        Test tasks/get method with real SUT communication.
        
        This method executes a real task retrieval call against the live SUT
        to validate task management protocol compliance.
        
        Args:
            context: Test execution context
            task_id: ID of task to retrieve
            history_length: Optional history length parameter
            
        Returns:
            TestResult with outcome from real SUT task retrieval
            
        Specification Reference: A2A Protocol v0.3.0 §7.2 - Task Management
        """
        pass
    
    @abstractmethod
    def test_cancel_task(self, context: TestContext, task_id: str) -> TestResult:
        """
        Test tasks/cancel method with real SUT communication.
        
        This method executes a real task cancellation call against the live SUT
        to validate task cancellation protocol compliance.
        
        Args:
            context: Test execution context
            task_id: ID of task to cancel
            
        Returns:
            TestResult with outcome from real SUT task cancellation
            
        Specification Reference: A2A Protocol v0.3.0 §7.2.2 - Task Cancellation
        """
        pass
    
    @abstractmethod
    def test_get_agent_card(self, context: TestContext) -> TestResult:
        """
        Test agent/card method with real SUT communication.
        
        This method executes a real agent card retrieval against the live SUT
        to validate agent discovery protocol compliance.
        
        Args:
            context: Test execution context
            
        Returns:
            TestResult with outcome from real SUT agent card retrieval
            
        Specification Reference: A2A Protocol v0.3.0 §5.5 - Agent Card Retrieval
        """
        pass
    
    # Common Test Patterns and Assertions
    
    def assert_valid_task_response(self, response: Dict[str, Any], context: TestContext) -> List[str]:
        """
        Assert that a task response is valid according to A2A specification.
        
        Args:
            response: Task response from real SUT
            context: Test execution context
            
        Returns:
            List of assertion failure messages (empty if all pass)
            
        Specification Reference: A2A Protocol v0.3.0 §7.2.1 - Task Object Schema
        """
        failures = []
        
        # Required fields for task object
        required_fields = ['taskId', 'state', 'createdAt']
        for field in required_fields:
            if field not in response:
                failures.append(f"Missing required field '{field}' in task response")
        
        # Validate task state
        if 'state' in response:
            valid_states = ['pending', 'in-progress', 'completed', 'failed', 'cancelled']
            if response['state'] not in valid_states:
                failures.append(f"Invalid task state '{response['state']}', must be one of {valid_states}")
        
        # Validate task ID format
        if 'taskId' in response:
            task_id = response['taskId']
            if not isinstance(task_id, str) or len(task_id) == 0:
                failures.append(f"Invalid taskId format: {task_id}")
        
        # Validate timestamp format
        if 'createdAt' in response:
            created_at = response['createdAt']
            if not isinstance(created_at, str):
                failures.append(f"Invalid createdAt format: {created_at}")
        
        return failures
    
    def assert_valid_agent_card(self, agent_card: Dict[str, Any], context: TestContext) -> List[str]:
        """
        Assert that an agent card is valid according to A2A specification.
        
        Args:
            agent_card: Agent card from real SUT
            context: Test execution context
            
        Returns:
            List of assertion failure messages (empty if all pass)
            
        Specification Reference: A2A Protocol v0.3.0 §5.1 - Agent Card Schema
        """
        failures = []
        
        # Required fields for agent card
        required_fields = ['protocol_version', 'name', 'endpoint']
        for field in required_fields:
            if field not in agent_card:
                failures.append(f"Missing required field '{field}' in agent card")
        
        # Validate protocol version
        if 'protocol_version' in agent_card:
            version = agent_card['protocol_version']
            if not version.startswith('0.3'):
                failures.append(f"Expected A2A v0.3.x protocol version, got '{version}'")
        
        # Validate name
        if 'name' in agent_card:
            name = agent_card['name']
            if not isinstance(name, str) or len(name) == 0:
                failures.append(f"Invalid agent name: {name}")
        
        # Validate endpoint
        if 'endpoint' in agent_card:
            endpoint = agent_card['endpoint']
            if not isinstance(endpoint, str) or not endpoint.startswith(('http://', 'https://', 'grpc://')):
                failures.append(f"Invalid endpoint format: {endpoint}")
        
        return failures
    
    def assert_transport_error_handling(self, error: Exception, context: TestContext) -> List[str]:
        """
        Assert that transport errors are handled correctly.
        
        Args:
            error: Exception raised during SUT communication
            context: Test execution context
            
        Returns:
            List of assertion failure messages (empty if all pass)
        """
        failures = []
        
        # Verify it's a proper transport error
        if not isinstance(error, TransportError):
            failures.append(f"Expected TransportError, got {type(error).__name__}")
            return failures
        
        # Verify transport type is correct
        if error.transport_type != self.transport_type:
            failures.append(f"Error transport type {error.transport_type} doesn't match adapter {self.transport_type}")
        
        # Verify error has meaningful message
        if not str(error).strip():
            failures.append("Transport error has empty message")
        
        return failures
    
    def execute_test_with_timing(self, test_func: Callable[[], Any], context: TestContext) -> tuple[Any, float]:
        """
        Execute a test function with timing measurement.
        
        Args:
            test_func: Function to execute
            context: Test execution context
            
        Returns:
            Tuple of (result, duration_ms)
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            result = test_func()
            
        finally:
            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000
        
        return result, duration_ms
    
    def create_test_result(self, outcome: TestOutcome, context: TestContext,
                          duration_ms: Optional[float] = None,
                          sut_response: Optional[Dict[str, Any]] = None,
                          error_message: Optional[str] = None,
                          assertions_passed: int = 0,
                          assertions_total: int = 0) -> TestResult:
        """
        Create a standardized test result.
        
        Args:
            outcome: Test outcome
            context: Test execution context
            duration_ms: Test execution duration
            sut_response: Response from real SUT
            error_message: Error message if test failed
            assertions_passed: Number of assertions that passed
            assertions_total: Total number of assertions
            
        Returns:
            TestResult object
        """
        return TestResult(
            outcome=outcome,
            test_name=context.test_name,
            transport_type=context.transport_type,
            spec_reference=context.spec_reference,
            duration_ms=duration_ms,
            sut_response=sut_response,
            error_message=error_message,
            assertions_passed=assertions_passed,
            assertions_total=assertions_total,
            metadata=context.metadata.copy()
        )
    
    # Transport-Specific Capability Testing
    
    def supports_streaming(self) -> bool:
        """
        Check if this transport supports streaming operations.
        
        Returns:
            True if streaming is supported
        """
        return hasattr(self.transport_client, 'send_streaming_message')
    
    def supports_bidirectional_streaming(self) -> bool:
        """
        Check if this transport supports bidirectional streaming.
        
        Returns:
            True if bidirectional streaming is supported
        """
        # Override in transport-specific adapters
        return False
    
    def supports_method(self, method_name: str) -> bool:
        """
        Check if this transport supports a specific A2A method.
        
        Args:
            method_name: Name of the A2A method
            
        Returns:
            True if the method is supported
        """
        return self.transport_client.supports_method(method_name)
    
    # Test Execution Framework
    
    def run_compliance_test_suite(self, test_scenarios: List[Dict[str, Any]], 
                                 context: TestContext) -> List[TestResult]:
        """
        Execute a complete compliance test suite against the real SUT.
        
        This method runs multiple test scenarios against the live SUT to validate
        comprehensive A2A protocol compliance across the transport.
        
        Args:
            test_scenarios: List of test scenario configurations
            context: Base test execution context
            
        Returns:
            List of TestResult objects from real SUT testing
        """
        results = []
        
        for scenario in test_scenarios:
            try:
                # Create scenario-specific context
                scenario_context = TestContext(
                    transport_type=context.transport_type,
                    sut_endpoint=context.sut_endpoint,
                    test_name=f"{context.test_name}::{scenario.get('name', 'unnamed')}",
                    spec_reference=scenario.get('spec_reference', context.spec_reference),
                    extra_headers=context.extra_headers.copy(),
                    timeout=scenario.get('timeout', context.timeout),
                    metadata=context.metadata.copy()
                )
                
                # Execute scenario-specific test
                scenario_type = scenario.get('type')
                if scenario_type == 'send_message':
                    result = self.test_send_message(scenario_context, scenario['message'])
                elif scenario_type == 'send_streaming_message':
                    result = self.test_send_streaming_message(scenario_context, scenario['message'])
                elif scenario_type == 'get_task':
                    result = self.test_get_task(scenario_context, scenario['task_id'], 
                                              scenario.get('history_length'))
                elif scenario_type == 'cancel_task':
                    result = self.test_cancel_task(scenario_context, scenario['task_id'])
                elif scenario_type == 'get_agent_card':
                    result = self.test_get_agent_card(scenario_context)
                else:
                    result = self.create_test_result(
                        TestOutcome.SKIP, scenario_context,
                        error_message=f"Unknown scenario type: {scenario_type}"
                    )
                
                results.append(result)
                
            except Exception as e:
                error_result = self.create_test_result(
                    TestOutcome.ERROR, scenario_context,
                    error_message=f"Test scenario execution failed: {e}"
                )
                results.append(error_result)
                self._logger.error(f"Test scenario failed: {e}", exc_info=True)
        
        return results
    
    def get_transport_info(self) -> Dict[str, Any]:
        """
        Get information about this transport adapter.
        
        Returns:
            Dictionary containing transport metadata
        """
        return {
            "adapter_class": self.__class__.__name__,
            "transport_type": self.transport_type.value,
            "sut_endpoint": self.sut_endpoint,
            "supports_streaming": self.supports_streaming(),
            "supports_bidirectional_streaming": self.supports_bidirectional_streaming(),
            "supported_methods": [
                method for method in [
                    "send_message", "send_streaming_message", "get_task", "cancel_task",
                    "get_agent_card", "get_authenticated_extended_card", "list_tasks"
                ] if self.supports_method(method)
            ]
        }
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.transport_type.value}, {self.sut_endpoint})"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(transport_type={self.transport_type!r}, sut_endpoint='{self.sut_endpoint}')"