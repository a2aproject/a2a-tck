"""Unit tests for the Agent Card utilities module."""

import requests
import responses

from tck import agent_card_utils
from tests.markers import optional_feature


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
            {"id": "skill1", "name": "Test Skill 1", "description": "First test skill", "inputOutputModes": ["text", "file"]},
            {
                "id": "skill2",
                "name": "Test Skill 2",
                "description": "Second test skill with data support",
                "inputOutputModes": ["text", "data"],
            },
        ],
    },
    "authentication": [{"scheme": "bearer", "description": "Bearer token authentication"}],
}

# Tests for fetch_agent_card


@optional_feature
@responses.activate
def test_fetch_agent_card_success():
    """OPTIONAL FEATURE: A2A Agent Card Utilities Testing

    Tests utility functions for Agent Card handling and parsing.
    These are feature tests for the TCK infrastructure itself.

    Failure Impact: Limits feature completeness (perfectly acceptable)
    Fix Suggestion: Implement comprehensive Agent Card parsing utilities

    Asserts:
        - Agent Card can be successfully retrieved from well-known endpoint
        - JSON parsing handles valid Agent Card data correctly
        - HTTP communication works as expected
    """
    # Mock the HTTP response
    responses.add(responses.GET, "https://example.com/.well-known/agent.json", json=SAMPLE_AGENT_CARD, status=200)

    # Create a session
    session = requests.Session()

    # Call the function
    result = agent_card_utils.fetch_agent_card("https://example.com/agent/jsonrpc", session)

    # Verify the result
    assert result == SAMPLE_AGENT_CARD
    assert responses.calls[0].request.url == "https://example.com/.well-known/agent.json"


@optional_feature
@responses.activate
def test_fetch_agent_card_not_found():
    """OPTIONAL FEATURE: A2A Agent Card Error Handling

    Tests error handling when Agent Card is not found.

    Failure Impact: Limits feature completeness (perfectly acceptable)
    Fix Suggestion: Implement robust error handling for missing Agent Cards

    Asserts:
        - 404 responses are handled gracefully
        - Function returns None for missing Agent Cards
        - Error conditions don't crash the application
    """
    # Mock a 404 response
    responses.add(responses.GET, "https://example.com/.well-known/agent.json", status=404)

    session = requests.Session()
    result = agent_card_utils.fetch_agent_card("https://example.com/agent/jsonrpc", session)

    # Function should return None
    assert result is None


@optional_feature
@responses.activate
def test_fetch_agent_card_invalid_json():
    """OPTIONAL FEATURE: A2A Agent Card JSON Error Handling

    Tests error handling when Agent Card contains invalid JSON.

    Failure Impact: Limits feature completeness (perfectly acceptable)
    Fix Suggestion: Implement robust JSON parsing with error handling

    Asserts:
        - Invalid JSON responses are handled gracefully
        - Function returns None for malformed data
        - JSON parsing errors don't crash the application
    """
    # Mock a response with invalid JSON
    responses.add(responses.GET, "https://example.com/.well-known/agent.json", body="this is not valid json", status=200)

    session = requests.Session()
    result = agent_card_utils.fetch_agent_card("https://example.com/agent/jsonrpc", session)

    # Function should return None
    assert result is None


# Tests for capability extraction functions


@optional_feature
def test_get_sut_rpc_endpoint():
    """OPTIONAL FEATURE: A2A RPC Endpoint Extraction

    Tests utility function for extracting RPC endpoint from Agent Card.

    Failure Impact: Limits feature completeness (perfectly acceptable)
    Fix Suggestion: Implement comprehensive endpoint extraction logic

    Asserts:
        - RPC endpoint can be extracted from various Agent Card formats
        - Function handles missing endpoints gracefully
        - Multiple endpoint location strategies work correctly
    """
    # Card with direct endpoint
    result1 = agent_card_utils.get_sut_rpc_endpoint(SAMPLE_AGENT_CARD)
    assert result1 == "https://example.com/agent/jsonrpc"

    # Card with endpoint in jsonrpc section
    card2 = {"jsonrpc": {"endpoint": "https://example.com/jsonrpc"}}
    result2 = agent_card_utils.get_sut_rpc_endpoint(card2)
    assert result2 == "https://example.com/jsonrpc"

    # Card with no endpoint
    result3 = agent_card_utils.get_sut_rpc_endpoint({})
    assert result3 is None


@optional_feature
def test_get_capability_streaming():
    """OPTIONAL FEATURE: A2A Streaming Capability Detection

    Tests utility function for detecting streaming capabilities.

    Failure Impact: Limits feature completeness (perfectly acceptable)
    Fix Suggestion: Implement comprehensive capability detection logic

    Asserts:
        - Streaming capability can be detected correctly
        - Boolean values are handled properly
        - Missing capabilities default to appropriate values
    """
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


@optional_feature
def test_get_capability_push_notifications():
    """OPTIONAL FEATURE: A2A Push Notifications Capability Detection

    Tests utility function for detecting push notification capabilities.

    Failure Impact: Limits feature completeness (perfectly acceptable)
    Fix Suggestion: Implement comprehensive push notification capability detection

    Asserts:
        - Push notification capability can be detected correctly
        - Boolean values are handled properly
        - Missing capabilities default to appropriate values
    """
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


@optional_feature
def test_get_supported_modalities():
    """OPTIONAL FEATURE: A2A Modality Support Detection

    Tests utility function for extracting supported modalities from Agent Card.

    Failure Impact: Limits feature completeness (perfectly acceptable)
    Fix Suggestion: Implement comprehensive modality detection and filtering

    Asserts:
        - Supported modalities can be extracted from skills
        - Skill-specific modality filtering works correctly
        - Missing skills are handled gracefully
    """
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


@optional_feature
def test_get_authentication_schemes():
    """OPTIONAL FEATURE: A2A Authentication Scheme Extraction

    Tests utility function for extracting authentication schemes from Agent Card.

    Failure Impact: Limits feature completeness (perfectly acceptable)
    Fix Suggestion: Implement comprehensive authentication scheme parsing

    Asserts:
        - Authentication schemes can be extracted correctly
        - Missing authentication sections are handled gracefully
        - Invalid authentication data doesn't crash the function
    """
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
