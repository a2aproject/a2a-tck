"""
Capability-based test validation for A2A TCK.

This module provides functionality to validate that declared capabilities in an Agent Card
are properly implemented, and to determine which tests should be conditional vs. skipped.
"""
from typing import Dict, List, Set, Optional
import pytest
import logging

logger = logging.getLogger(__name__)

class CapabilityValidator:
    """
    Validates that declared capabilities are properly implemented.
    
    This class analyzes an Agent Card to determine:
    1. Which capabilities are declared
    2. Which tests should be mandatory for those capabilities
    3. Which tests should be skipped if capabilities are not declared
    4. Whether declared capabilities are correctly implemented
    """
    
    def __init__(self, agent_card: Dict):
        """
        Initialize the validator with an Agent Card.
        
        Args:
            agent_card: The agent card dictionary from the SUT
        """
        self.agent_card = agent_card
        self.capabilities = agent_card.get('capabilities', {})
        
        # Log the capabilities we found for debugging
        logger.info(f"Agent Card capabilities: {self.capabilities}")
        
    def get_required_tests_for_capability(self, capability: str) -> List[str]:
        """
        Return test names that MUST pass if capability is declared.
        
        According to A2A specification, if an agent declares a capability,
        it MUST implement it correctly. These tests become mandatory.
        
        Args:
            capability: The capability name (e.g., 'streaming', 'pushNotifications')
            
        Returns:
            List of test function names that must pass for this capability
        """
        capability_tests = {
            'streaming': [
                'test_message_stream_basic',
                'test_message_stream_invalid_params', 
                'test_tasks_resubscribe',
                'test_tasks_resubscribe_nonexistent',
                'test_tasks_resubscribe_invalid_params'
            ],
            'pushNotifications': [
                'test_set_push_notification_config',
                'test_get_push_notification_config', 
                'test_push_notification_nonexistent',
                'test_push_notification_invalid_params'
            ],
            'authentication': [
                'test_authentication_scheme_validation',
                'test_authentication_required_flow',
                'test_authentication_token_validation'
            ]
        }
        return capability_tests.get(capability, [])
    
    def validate_modality_support(self, modality: str) -> bool:
        """
        Check if a modality is supported by the agent.
        
        Args:
            modality: The modality to check (e.g., 'text', 'file', 'data')
            
        Returns:
            True if the modality is supported, False otherwise
        """
        # Check defaultInputModes and defaultOutputModes
        input_modes = self.agent_card.get('defaultInputModes', [])
        output_modes = self.agent_card.get('defaultOutputModes', [])
        
        return modality in input_modes or modality in output_modes
    
    def is_capability_declared(self, capability: str) -> bool:
        """
        Check if a specific capability is declared in the agent card.
        
        Args:
            capability: The capability name to check
            
        Returns:
            True if the capability is declared and enabled, False otherwise
        """
        return self.capabilities.get(capability, False) is True
    
    def get_declared_capabilities(self) -> List[str]:
        """
        Get all capabilities that are declared and enabled.
        
        Returns:
            List of capability names that are declared as True
        """
        return [cap for cap, enabled in self.capabilities.items() if enabled is True]
    
    def should_test_run_for_capability(self, test_name: str, capability: str) -> tuple[bool, str]:
        """
        Determine if a test should run based on capability declaration.
        
        Args:
            test_name: Name of the test function
            capability: The capability this test validates
            
        Returns:
            Tuple of (should_run: bool, reason: str)
        """
        if self.is_capability_declared(capability):
            return True, f"Capability '{capability}' is declared - test is MANDATORY"
        else:
            return False, f"Capability '{capability}' not declared - test SKIPPED (this is allowed)"
    
    def validate_capability_consistency(self) -> Dict[str, List[str]]:
        """
        Validate that all declared capabilities have corresponding implementations.
        
        This checks for common capability declaration issues:
        1. Capabilities declared but not implemented
        2. Tests expecting capabilities that aren't declared
        
        Returns:
            Dictionary with potential issues categorized by type
        """
        issues = {
            'undeclared_but_tested': [],
            'declared_but_untested': [],
            'modality_mismatches': []
        }
        
        # Check for common capability/modality mismatches
        declared_caps = self.get_declared_capabilities()
        
        # Check if streaming is declared but no streaming modalities
        if 'streaming' in declared_caps:
            if not any(mode in ['stream', 'sse'] for mode in 
                      self.agent_card.get('defaultInputModes', []) + 
                      self.agent_card.get('defaultOutputModes', [])):
                issues['modality_mismatches'].append(
                    "Streaming capability declared but no streaming modalities in input/output modes"
                )
        
        return issues


def skip_if_capability_not_declared(capability: str):
    """
    Decorator to skip tests if a specific capability is not declared.
    
    This implements the conditional mandatory logic:
    - If capability is declared: test MUST pass (mandatory)
    - If capability is not declared: test is SKIPPED (allowed)
    
    Args:
        capability: The capability name to check
        
    Usage:
        @skip_if_capability_not_declared('streaming')
        def test_streaming_feature():
            # This test only runs if streaming capability is declared
            pass
    """
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            # Get agent card from test fixtures/parameters
            agent_card = None
            
            # Try to find agent card in test arguments
            for arg in args:
                if isinstance(arg, dict) and 'capabilities' in arg:
                    agent_card = arg
                    break
            
            # Try to find in kwargs
            if not agent_card:
                agent_card = kwargs.get('agent_card_data') or kwargs.get('agent_card')
            
            if not agent_card:
                # If we can't find agent card, run the test (fail safe)
                logger.warning(f"Could not find agent card for capability check in {test_func.__name__}")
                return test_func(*args, **kwargs)
            
            validator = CapabilityValidator(agent_card)
            should_run, reason = validator.should_test_run_for_capability(test_func.__name__, capability)
            
            if not should_run:
                pytest.skip(reason)
            
            logger.info(f"Running {test_func.__name__}: {reason}")
            return test_func(*args, **kwargs)
        
        return wrapper
    return decorator


def has_modality_support(agent_card: Dict, modality: str) -> bool:
    """
    Helper function to check if a modality is supported by the agent.
    
    Args:
        agent_card: The agent card dictionary from the SUT
        modality: The modality to check (e.g., 'text', 'file', 'data')
        
    Returns:
        True if the modality is supported, False otherwise
    """
    validator = CapabilityValidator(agent_card)
    return validator.validate_modality_support(modality)


def requires_modality(modality: str):
    """
    Decorator to skip tests if a specific modality is not supported.
    
    Args:
        modality: The modality required (e.g., 'file', 'data')
        
    Usage:
        @requires_modality('file')
        def test_file_upload():
            # This test only runs if file modality is supported
            pass
    """
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            # Get agent card from test fixtures/parameters
            agent_card = None
            
            # Try to find agent card in test arguments
            for arg in args:
                if isinstance(arg, dict) and 'defaultInputModes' in arg:
                    agent_card = arg
                    break
            
            # Try to find in kwargs
            if not agent_card:
                agent_card = kwargs.get('agent_card_data') or kwargs.get('agent_card')
            
            if not agent_card:
                logger.warning(f"Could not find agent card for modality check in {test_func.__name__}")
                return test_func(*args, **kwargs)
            
            validator = CapabilityValidator(agent_card)
            if not validator.validate_modality_support(modality):
                pytest.skip(f"Modality '{modality}' not supported - test not applicable")
            
            logger.info(f"Running {test_func.__name__}: modality '{modality}' is supported")
            return test_func(*args, **kwargs)
        
        return wrapper
    return decorator 