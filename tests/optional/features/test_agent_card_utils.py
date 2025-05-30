"""
Unit tests for the Agent Card utilities module.
"""

import json
from unittest.mock import MagicMock, patch

import requests
import responses

from tck import agent_card_utils

# Sample valid Agent Card for testing
SAMPLE_AGENT_CARD = {
    "name": "Test Agent",
    "description": "A test agent for TCK",
    "id": "test-agent-id",
    "protocolVersion": "1.0",
    "url": "https://example.com/agent",
    "endpoint": "https://example.com/agent/jsonrpc",
    "capabilities": {
        "streaming": True,
        "pushNotifications": False,
        "skills": [
            {
                "id": "skill1",
                "name": "Test Skill 1",
                "description": "First test skill",
                "inputOutputModes": ["text", "file"]
            },
            {
                "id": "skill2",
                "name": "Test Skill 2",
                "description": "Second test skill with data support",
                "inputOutputModes": ["text", "data"]
            }
        ]
    },
    "authentication": [
        {
            "scheme": "bearer",
            "description": "Bearer token authentication"
        }
    ]
}

# Tests for fetch_agent_card

@responses.activate
def test_fetch_agent_card_success():
    """Test successful retrieval of Agent Card."""
    # Mock the HTTP response
    responses.add(
        responses.GET,
        "https://example.com/.well-known/agent.json",
        json=SAMPLE_AGENT_CARD,
        status=200
    )
    
    # Create a session
    session = requests.Session()
    
    # Call the function
    result = agent_card_utils.fetch_agent_card("https://example.com/agent/jsonrpc", session)
    
    # Verify the result
    assert result == SAMPLE_AGENT_CARD
    assert responses.calls[0].request.url == "https://example.com/.well-known/agent.json"

@responses.activate
def test_fetch_agent_card_not_found():
    """Test handling of 404 response when Agent Card is not found."""
    # Mock a 404 response
    responses.add(
        responses.GET,
        "https://example.com/.well-known/agent.json",
        status=404
    )
    
    session = requests.Session()
    result = agent_card_utils.fetch_agent_card("https://example.com/agent/jsonrpc", session)
    
    # Function should return None
    assert result is None

@responses.activate
def test_fetch_agent_card_invalid_json():
    """Test handling of invalid JSON in Agent Card response."""
    # Mock a response with invalid JSON
    responses.add(
        responses.GET,
        "https://example.com/.well-known/agent.json",
        body="this is not valid json",
        status=200
    )
    
    session = requests.Session()
    result = agent_card_utils.fetch_agent_card("https://example.com/agent/jsonrpc", session)
    
    # Function should return None
    assert result is None

# Tests for capability extraction functions

def test_get_sut_rpc_endpoint():
    """Test extracting RPC endpoint from Agent Card."""
    # Card with direct endpoint
    result1 = agent_card_utils.get_sut_rpc_endpoint(SAMPLE_AGENT_CARD)
    assert result1 == "https://example.com/agent/jsonrpc"
    
    # Card with endpoint in jsonrpc section
    card2 = {
        "jsonrpc": {
            "endpoint": "https://example.com/jsonrpc"
        }
    }
    result2 = agent_card_utils.get_sut_rpc_endpoint(card2)
    assert result2 == "https://example.com/jsonrpc"
    
    # Card with no endpoint
    result3 = agent_card_utils.get_sut_rpc_endpoint({})
    assert result3 is None

def test_get_capability_streaming():
    """Test checking streaming capability in Agent Card."""
    # Card with streaming=True
    result1 = agent_card_utils.get_capability_streaming(SAMPLE_AGENT_CARD)
    assert result1 is True
    
    # Card with streaming=False
    card2 = {"capabilities": {"streaming": False}}
    result2 = agent_card_utils.get_capability_streaming(card2)
    assert result2 is False
    
    # Card with no streaming capability
    result3 = agent_card_utils.get_capability_streaming({})
    assert result3 is False
    
    # Card with invalid streaming value (should coerce to boolean)
    card4 = {"capabilities": {"streaming": "yes"}}
    result4 = agent_card_utils.get_capability_streaming(card4)
    assert result4 is True

def test_get_capability_push_notifications():
    """Test checking push notifications capability in Agent Card."""
    # Card with pushNotifications=False
    result1 = agent_card_utils.get_capability_push_notifications(SAMPLE_AGENT_CARD)
    assert result1 is False
    
    # Card with pushNotifications=True
    card2 = {"capabilities": {"pushNotifications": True}}
    result2 = agent_card_utils.get_capability_push_notifications(card2)
    assert result2 is True
    
    # Card with no pushNotifications capability
    result3 = agent_card_utils.get_capability_push_notifications({})
    assert result3 is False

def test_get_supported_modalities():
    """Test extracting supported modalities from Agent Card."""
    # Get all modalities from sample card
    result1 = agent_card_utils.get_supported_modalities(SAMPLE_AGENT_CARD)
    # Order doesn't matter, so convert to set for comparison
    assert set(result1) == {"text", "file", "data"}
    
    # Get modalities for specific skill
    result2 = agent_card_utils.get_supported_modalities(SAMPLE_AGENT_CARD, skill_id="skill1")
    assert set(result2) == {"text", "file"}
    
    # Card with no skills
    result3 = agent_card_utils.get_supported_modalities({})
    assert result3 == []
    
    # Card with non-existent skill ID
    result4 = agent_card_utils.get_supported_modalities(SAMPLE_AGENT_CARD, skill_id="nonexistent")
    assert result4 == []

def test_get_authentication_schemes():
    """Test extracting authentication schemes from Agent Card."""
    # Get authentication schemes from sample card
    result1 = agent_card_utils.get_authentication_schemes(SAMPLE_AGENT_CARD)
    assert result1 == [{"scheme": "bearer", "description": "Bearer token authentication"}]
    
    # Card with no authentication
    result2 = agent_card_utils.get_authentication_schemes({})
    assert result2 == []
    
    # Card with invalid authentication (not a list)
    card3 = {"authentication": "invalid"}
    result3 = agent_card_utils.get_authentication_schemes(card3)
    assert result3 == [] 