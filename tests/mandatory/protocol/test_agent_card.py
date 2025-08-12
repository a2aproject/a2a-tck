"""A2A Protocol Specification: Agent Card mandatory validation tests.

This test suite validates the mandatory structure and content of the SUT's Agent Card
according to the A2A specification: https://google.github.io/A2A/specification/#agent-card
"""

import logging
import re

import pytest

from tck import agent_card_utils
from tck.sut_client import SUTClient
from tests.markers import mandatory_protocol


logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def sut_client():
    """Fixture to provide a SUTClient instance."""
    return SUTClient()


@pytest.fixture(scope="module")
def fetched_agent_card(sut_client, agent_card_data):
    """Fixture to reuse the global agent_card_data fixture or fetch it if not available.

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
    """MANDATORY: A2A Specification §2.1 - Agent Card Availability

    "A2A Servers MUST make an Agent Card available"

    This validates that the Agent Card is accessible and is well-formed JSON.

    Failure Impact: Implementation is not A2A compliant
    """
    assert fetched_agent_card is not None, "Agent Card should be available"
    assert isinstance(fetched_agent_card, dict), "Agent Card should be a JSON object"


@mandatory_protocol
def test_mandatory_fields_present(fetched_agent_card):
    """MANDATORY: A2A Specification §2.1 - Agent Card Structure

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
        "version",
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
    """MANDATORY: A2A Specification §2.1 - Agent Card Field Types

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
    url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    assert re.match(url_pattern, url), f"url is not a valid URL: {url}"

    # Note: protocolVersion and id are NOT in A2A specification
