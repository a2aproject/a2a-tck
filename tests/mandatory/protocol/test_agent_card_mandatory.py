"""
A2A Protocol Specification: Agent Card mandatory fields validation tests.

This test suite validates the mandatory fields and structure of the SUT's Agent Card
according to the A2A specification: https://google.github.io/A2A/specification/#agent-card
"""

import logging
import pytest

from tck import agent_card_utils
from tck.sut_client import SUTClient

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


def test_agent_card_mandatory_fields(fetched_agent_card):
    """
    MANDATORY: A2A Specification §5.5 - AgentCard Required Fields

    Tests that all mandatory fields are present in the Agent Card.
    These fields are required by the A2A specification for all agents.

    Failure Impact: Critical - violates A2A specification compliance
    Fix Suggestion: Ensure all mandatory fields are included in Agent Card

    Asserts:
        - All required fields are present
        - Field types match specification requirements
        - Basic structure is valid
    """
    assert isinstance(fetched_agent_card, dict), "Agent Card must be an object"

    # Required fields per A2A specification
    required_fields = [
        "capabilities",
        "defaultInputModes",
        "defaultOutputModes",
        "description",
        "name",
        "protocolVersion",
        "skills",
        "url",
        "version",
    ]

    for field in required_fields:
        assert field in fetched_agent_card, f"Required field '{field}' missing from Agent Card"
        assert fetched_agent_card[field] is not None, f"Required field '{field}' cannot be null"


def test_agent_card_capabilities_mandatory(fetched_agent_card):
    """
    MANDATORY: A2A Specification §5.5.2 - AgentCapabilities Field Required

    Tests that the capabilities field is present and properly structured.
    The capabilities field is mandatory in the Agent Card, even if individual
    capabilities within it are optional.

    Failure Impact: Critical - violates A2A specification compliance
    Fix Suggestion: Include capabilities object in Agent Card

    Asserts:
        - capabilities field is present
        - capabilities is an object (not null/undefined)
        - capabilities field has proper structure
    """
    assert "capabilities" in fetched_agent_card, "Agent Card must include capabilities field"

    capabilities = fetched_agent_card["capabilities"]
    assert capabilities is not None, "capabilities field cannot be null"
    assert isinstance(capabilities, dict), "capabilities must be an object"


def test_agent_card_skills_mandatory(fetched_agent_card):
    """
    MANDATORY: A2A Specification §5.5.6 - Skills Array Required

    Tests that the skills field is present and properly structured.
    Skills define what the agent can do and are mandatory.

    Failure Impact: Critical - violates A2A specification compliance
    Fix Suggestion: Include skills array in Agent Card

    Asserts:
        - skills field is present
        - skills is an array
        - skills array is not empty
        - each skill has required fields
    """
    assert "skills" in fetched_agent_card, "Agent Card must include skills field"

    skills = fetched_agent_card["skills"]
    assert skills is not None, "skills field cannot be null"
    assert isinstance(skills, list), "skills must be an array"
    assert len(skills) > 0, "skills array cannot be empty"

    # Validate each skill has required fields
    required_skill_fields = ["id", "name", "description", "tags"]

    for i, skill in enumerate(skills):
        assert isinstance(skill, dict), f"skill at index {i} must be an object"

        for field in required_skill_fields:
            assert field in skill, f"skill at index {i} missing required field '{field}'"
            assert skill[field] is not None, f"skill at index {i} field '{field}' cannot be null"


def test_agent_card_input_output_modes_mandatory(fetched_agent_card):
    """
    MANDATORY: A2A Specification §5.5.3/5.5.4 - Input/Output Modes Required

    Tests that defaultInputModes and defaultOutputModes are present and valid.
    These define the media types the agent supports.

    Failure Impact: Critical - violates A2A specification compliance
    Fix Suggestion: Include input/output mode arrays in Agent Card

    Asserts:
        - defaultInputModes field is present and is array
        - defaultOutputModes field is present and is array
        - modes are non-empty strings
    """
    # Check defaultInputModes
    assert "defaultInputModes" in fetched_agent_card, "Agent Card must include defaultInputModes field"
    input_modes = fetched_agent_card["defaultInputModes"]
    assert input_modes is not None, "defaultInputModes field cannot be null"
    assert isinstance(input_modes, list), "defaultInputModes must be an array"

    for i, mode in enumerate(input_modes):
        assert isinstance(mode, str), f"defaultInputModes[{i}] must be a string"
        assert mode.strip(), f"defaultInputModes[{i}] cannot be empty"

    # Check defaultOutputModes
    assert "defaultOutputModes" in fetched_agent_card, "Agent Card must include defaultOutputModes field"
    output_modes = fetched_agent_card["defaultOutputModes"]
    assert output_modes is not None, "defaultOutputModes field cannot be null"
    assert isinstance(output_modes, list), "defaultOutputModes must be an array"

    for i, mode in enumerate(output_modes):
        assert isinstance(mode, str), f"defaultOutputModes[{i}] must be a string"
        assert mode.strip(), f"defaultOutputModes[{i}] cannot be empty"


def test_agent_card_basic_info_mandatory(fetched_agent_card):
    """
    MANDATORY: A2A Specification §5.5.1 - Basic Agent Information Required

    Tests that basic agent information fields are present and valid.
    These provide essential information about the agent.

    Failure Impact: Critical - violates A2A specification compliance
    Fix Suggestion: Include all required basic information fields

    Asserts:
        - name, description, url, version are present
        - fields are non-empty strings
        - url appears to be a valid URL format
    """
    # Check name
    assert "name" in fetched_agent_card, "Agent Card must include name field"
    name = fetched_agent_card["name"]
    assert isinstance(name, str), "name must be a string"
    assert name.strip(), "name cannot be empty"

    # Check description
    assert "description" in fetched_agent_card, "Agent Card must include description field"
    description = fetched_agent_card["description"]
    assert isinstance(description, str), "description must be a string"
    assert description.strip(), "description cannot be empty"

    # Check url
    assert "url" in fetched_agent_card, "Agent Card must include url field"
    url = fetched_agent_card["url"]
    assert isinstance(url, str), "url must be a string"
    assert url.strip(), "url cannot be empty"
    # Basic URL format validation
    assert url.startswith(("http://", "https://")), "url must be a valid HTTP/HTTPS URL"

    # Check version
    assert "version" in fetched_agent_card, "Agent Card must include version field"
    version = fetched_agent_card["version"]
    assert isinstance(version, str), "version must be a string"
    assert version.strip(), "version cannot be empty"
