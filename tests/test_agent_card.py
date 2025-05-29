"""
A2A Protocol Specification: Agent Card validation tests.

This test suite validates the structure and content of the SUT's Agent Card
according to the A2A specification: https://google.github.io/A2A/specification/#agent-card
"""

import logging
import re

import pytest

from tck import agent_card_utils
from tck.sut_client import SUTClient
from tests.markers import mandatory_protocol, optional_capability

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def sut_client():
    """Fixture to provide a SUTClient instance."""
    return SUTClient()

@pytest.fixture(scope="module")
def fetched_agent_card(sut_client, agent_card_data):
    """
    Fixture to reuse the global agent_card_data fixture or fetch it if not available.
    
    This adds an extra layer to handle cases where the agent_card_data fixture might be None
    because of the --skip-agent-card flag.
    """
    if agent_card_data is not None:
        return agent_card_data
    
    # Try to fetch it directly for this test suite
    logger.info("Global agent_card_data is None, attempting to fetch directly")
    agent_card = agent_card_utils.fetch_agent_card(sut_client.base_url, sut_client.session)
    
    if agent_card is None:
        pytest.skip("Failed to fetch Agent Card - skipping Agent Card validation tests")
    
    return agent_card

@mandatory_protocol
def test_agent_card_available(fetched_agent_card):
    """
    MANDATORY: A2A Specification §2.1 - Agent Card Availability
    
    "A2A Servers MUST make an Agent Card available"
    
    This validates that the Agent Card is accessible and is well-formed JSON.
    
    Failure Impact: Implementation is not A2A compliant
    """
    assert fetched_agent_card is not None, "Agent Card should be available"
    assert isinstance(fetched_agent_card, dict), "Agent Card should be a JSON object"

@mandatory_protocol
def test_mandatory_fields_present(fetched_agent_card):
    """
    MANDATORY: A2A Specification §2.1 - Agent Card Structure
    
    The A2A JSON Schema defines required fields in AgentCard.
    These fields are MANDATORY for A2A compliance.
    
    Failure Impact: Implementation is not A2A compliant
    """
    # Based on the A2A JSON schema, these fields are actually required
    mandatory_fields = [
        "capabilities", 
        "defaultInputModes", 
        "defaultOutputModes", 
        "description", 
        "name", 
        "skills", 
        "url", 
        "version"
    ]
    
    # Fields that were previously expected but are NOT in the specification
    non_spec_fields = ["protocolVersion", "id"]
    
    # Check each mandatory field is present
    for field in mandatory_fields:
        assert field in fetched_agent_card, f"Agent Card missing required field: {field} (A2A spec requirement)"
    
    # Document that these fields are NOT in the specification
    for field in non_spec_fields:
        if field in fetched_agent_card:
            # If SDK provides them, that's fine but not required
            pass
        else:
            # This is expected - these fields are not in the specification
            pass

@mandatory_protocol
def test_mandatory_field_types(fetched_agent_card):
    """
    MANDATORY: A2A Specification §2.1 - Agent Card Field Types
    
    The A2A JSON Schema defines required types for mandatory fields.
    Incorrect types violate the A2A specification.
    
    Failure Impact: Implementation is not A2A compliant
    """
    # Check types of required fields according to A2A specification
    assert isinstance(fetched_agent_card.get("name"), str), "name must be a string"
    assert isinstance(fetched_agent_card.get("description"), str), "description must be a string"
    assert isinstance(fetched_agent_card.get("version"), str), "version must be a string"
    assert isinstance(fetched_agent_card.get("url"), str), "url must be a string"
    assert isinstance(fetched_agent_card.get("capabilities"), dict), "capabilities must be an object"
    assert isinstance(fetched_agent_card.get("defaultInputModes"), list), "defaultInputModes must be an array"
    assert isinstance(fetched_agent_card.get("defaultOutputModes"), list), "defaultOutputModes must be an array"
    assert isinstance(fetched_agent_card.get("skills"), list), "skills must be an array"
    
    # Simple regex to check for a valid URL format
    url = fetched_agent_card["url"]
    url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    assert re.match(url_pattern, url), f"url is not a valid URL: {url}"
    
    # Note: protocolVersion and id are NOT in A2A specification

@optional_capability  
def test_capabilities_structure(fetched_agent_card):
    """
    OPTIONAL: A2A Specification §2.1 - Capabilities Structure
    
    While the capabilities field itself is MANDATORY, the specific
    capabilities (streaming, pushNotifications, etc.) are optional.
    This validates their structure if present.
    
    Status: Optional validation of capability structure
    """
    # Skip if capabilities is not present (it's optional)
    if "capabilities" not in fetched_agent_card:
        pytest.skip("Agent Card does not have a capabilities section")
    
    capabilities = fetched_agent_card["capabilities"]
    assert isinstance(capabilities, dict), "capabilities must be an object"
    
    # Check streaming capability if present
    if "streaming" in capabilities:
        assert isinstance(capabilities["streaming"], bool), "streaming capability must be a boolean"
    
    # Check pushNotifications capability if present
    if "pushNotifications" in capabilities:
        assert isinstance(capabilities["pushNotifications"], bool), "pushNotifications capability must be a boolean"
    
    # Check skills if present
    if "skills" in capabilities:
        skills = capabilities["skills"]
        assert isinstance(skills, list), "skills must be an array"
        
        # Validate each skill
        for i, skill in enumerate(skills):
            assert isinstance(skill, dict), f"skill at index {i} must be an object"
            assert "id" in skill, f"skill at index {i} missing id"
            assert "name" in skill, f"skill at index {i} missing name"
            assert "description" in skill, f"skill at index {i} missing description"
            
            # Check input/output modes if present
            if "inputOutputModes" in skill:
                modes = skill["inputOutputModes"]
                assert isinstance(modes, list), f"inputOutputModes in skill {skill['id']} must be an array"
                for mode in modes:
                    assert isinstance(mode, str), f"mode in skill {skill['id']} must be a string"

@optional_capability
def test_authentication_structure(fetched_agent_card):
    """
    OPTIONAL: A2A Specification §4.1 - Authentication Structure
    
    Authentication schemes are optional capabilities. This validates
    their structure if present, but does not require them.
    
    Status: Optional validation of authentication structure
    """
    # Skip if authentication is not present (it's optional)
    if "authentication" not in fetched_agent_card:
        pytest.skip("Agent Card does not have an authentication section")
    
    auth = fetched_agent_card["authentication"]
    assert isinstance(auth, list), "authentication must be an array"
    
    # Validate each authentication scheme
    for i, scheme in enumerate(auth):
        assert isinstance(scheme, dict), f"authentication scheme at index {i} must be an object"
        assert "scheme" in scheme, f"authentication scheme at index {i} missing scheme property"
        assert isinstance(scheme["scheme"], str), f"scheme property in authentication scheme at index {i} must be a string"
        
        # Check known schemes and their required properties
        scheme_type = scheme["scheme"].lower()
        
        if scheme_type == "bearer":
            # Bearer token might have optional tokenUrl
            if "tokenUrl" in scheme:
                assert isinstance(scheme["tokenUrl"], str), "tokenUrl must be a string"
        
        elif scheme_type == "basic":
            # Basic auth typically doesn't require additional fields
            pass
        
        elif scheme_type == "apikey":
            # API key auth might specify name and location
            if "name" in scheme:
                assert isinstance(scheme["name"], str), "name in apikey scheme must be a string"
            if "in" in scheme:
                assert scheme["in"] in ["header", "query", "cookie"], "in property must be one of: header, query, cookie"

# Additional tests will be added for the structure and content of the Agent Card:
# - EXT-2.2: Validate Mandatory Agent Card Fields
# - EXT-2.3: Validate Agent Card capabilities Structure
# - EXT-2.4: Validate Agent Card authentication Structure 