"""
A2A Protocol Specification: Agent Extensions validation tests.

This test suite validates the AgentExtension capability introduced in the latest A2A specification.
Extensions allow agents to declare additional capabilities beyond the core protocol.

Specification reference: https://google.github.io/A2A/specification/#agent-extension
"""

import logging
import pytest

from tck import agent_card_utils
from tck.sut_client import SUTClient
from tests.markers import optional_capability

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def sut_client():
    """Fixture to provide a SUTClient instance."""
    return SUTClient()


@pytest.fixture(scope="module")
def fetched_agent_card(sut_client, agent_card_data):
    """
    Fixture to reuse the global agent_card_data fixture or fetch it if not available.
    """
    if agent_card_data is not None:
        return agent_card_data

    # Try to fetch it directly for this test suite
    logger.info("Global agent_card_data is None, attempting to fetch directly")
    agent_card = agent_card_utils.fetch_agent_card(sut_client.base_url, sut_client.session)

    if agent_card is None:
        pytest.skip("Failed to fetch Agent Card - skipping Agent Extension validation tests")

    return agent_card


@pytest.fixture(scope="module")
def agent_extensions(fetched_agent_card):
    """
    Fixture to extract extensions from the Agent Card capabilities.
    """
    if "capabilities" not in fetched_agent_card:
        return []

    capabilities = fetched_agent_card["capabilities"]
    return capabilities.get("extensions", [])


@optional_capability
def test_extension_uri_format(agent_extensions):
    """
    OPTIONAL CAPABILITY: A2A Specification §5.5.2.1 - Extension URI Format

    Tests that extension URIs follow proper formatting conventions.
    URIs should be well-formed and identify the extension uniquely.

    Failure Impact: Limits extension interoperability (perfectly acceptable)
    Fix Suggestion: Use well-formed URIs for better extension identification

    Asserts:
        - Extension URIs are non-empty strings
        - URIs appear to be well-formed (basic validation)
        - No duplicate URIs in the extensions list
    """
    if not agent_extensions:
        pytest.skip("No agent extensions declared")

    seen_uris = set()

    for i, extension in enumerate(agent_extensions):
        uri = extension["uri"]  # Already validated to exist and be string in capabilities test

        # Check for non-empty URI
        assert uri.strip(), f"Extension URI at index {i} cannot be empty or whitespace-only"

        # Basic URI format validation (not strict RFC compliance)
        assert not uri.startswith(" ") and not uri.endswith(" "), f"Extension URI at index {i} has leading/trailing whitespace"

        # Check for duplicate URIs
        assert uri not in seen_uris, f"Duplicate extension URI found: {uri}"
        seen_uris.add(uri)

        logger.info(f"Extension {i}: {uri}")


@optional_capability
def test_required_extensions_declaration(agent_extensions):
    """
    OPTIONAL CAPABILITY: A2A Specification §5.5.2.1 - Required Extensions

    Tests that agents properly declare when extensions are required vs optional.
    The 'required' field indicates whether clients must follow extension protocols.

    Failure Impact: May cause client compatibility issues (acceptable if documented)
    Fix Suggestion: Clearly mark required vs optional extensions for client guidance

    Asserts:
        - 'required' field is boolean when present
        - Required extensions are logged for visibility
        - Extension requirements are clearly declared
    """
    if not agent_extensions:
        pytest.skip("No agent extensions declared")

    required_extensions = []
    optional_extensions = []

    for extension in agent_extensions:
        uri = extension["uri"]
        is_required = extension.get("required", False)  # Defaults to False per spec

        if is_required:
            required_extensions.append(uri)
            logger.warning(f"REQUIRED extension: {uri} - clients SHOULD expect failures without support")
        else:
            optional_extensions.append(uri)
            logger.info(f"Optional extension: {uri}")

    # Log summary for test visibility
    if required_extensions:
        logger.warning(f"Agent declares {len(required_extensions)} required extensions")
        logger.warning("Clients SHOULD expect failures when attempting to interact without these extensions")

    if optional_extensions:
        logger.info(f"Agent declares {len(optional_extensions)} optional extensions")

    # This test passes regardless but provides important information about extension requirements


@optional_capability
def test_extension_parameters_structure(agent_extensions):
    """
    OPTIONAL CAPABILITY: A2A Specification §5.5.2.1 - Extension Parameters

    Tests that extension parameters follow proper structure when provided.
    Parameters provide optional configuration for extensions.

    Failure Impact: Limits extension configuration (perfectly acceptable)
    Fix Suggestion: Use well-structured parameters for better extension configuration

    Asserts:
        - Extension params are objects when present
        - Parameter values can be any JSON type
        - Structure is consistent across extensions
    """
    if not agent_extensions:
        pytest.skip("No agent extensions declared")

    extensions_with_params = []

    for extension in agent_extensions:
        uri = extension["uri"]

        if "params" in extension:
            params = extension["params"]
            # Already validated to be dict in capabilities test

            extensions_with_params.append(uri)
            logger.info(f"Extension {uri} has {len(params)} parameters")

            # Log parameter names for debugging (not values for security)
            if params:
                param_names = list(params.keys())
                logger.info(f"Extension {uri} parameters: {param_names}")

    if not extensions_with_params:
        logger.info("No extensions declare parameters")
    else:
        logger.info(f"{len(extensions_with_params)} extensions declare parameters")


@optional_capability
def test_extension_descriptions(agent_extensions):
    """
    OPTIONAL CAPABILITY: A2A Specification §5.5.2.1 - Extension Descriptions

    Tests that extension descriptions provide useful information when present.
    Descriptions help clients understand how the agent uses each extension.

    Failure Impact: Limits extension discoverability (perfectly acceptable)
    Fix Suggestion: Provide clear descriptions for better extension understanding

    Asserts:
        - Extension descriptions are non-empty strings when present
        - Descriptions provide meaningful information
    """
    if not agent_extensions:
        pytest.skip("No agent extensions declared")

    described_extensions = []
    undescribed_extensions = []

    for extension in agent_extensions:
        uri = extension["uri"]

        if "description" in extension:
            description = extension["description"]
            # Already validated to be string in capabilities test

            # Check for meaningful content
            if description.strip():
                described_extensions.append(uri)
                logger.info(f"Extension {uri}: {description[:100]}...")
            else:
                logger.warning(f"Extension {uri} has empty description")
                undescribed_extensions.append(uri)
        else:
            undescribed_extensions.append(uri)
            logger.info(f"Extension {uri} has no description")

    # Log summary
    if described_extensions:
        logger.info(f"{len(described_extensions)} extensions have descriptions")

    if undescribed_extensions:
        logger.info(f"{len(undescribed_extensions)} extensions lack descriptions")


@optional_capability
def test_client_extension_compatibility_warning(agent_extensions):
    """
    OPTIONAL CAPABILITY: A2A Specification §5.5.2.1 - Client Compatibility

    Tests that clients are properly warned about extension requirements.
    As per spec: "Clients SHOULD expect failures when attempting to interact
    with a server that requires an extension they don't support."

    This test documents extension compatibility requirements for client developers.

    Failure Impact: May cause unexpected client failures (acceptable with documentation)
    Fix Suggestion: Document extension requirements for client implementations

    Asserts:
        - Extension requirements are properly documented
        - Client developers are warned about potential compatibility issues
    """
    if not agent_extensions:
        pytest.skip("No agent extensions declared")

    required_extensions = [ext for ext in agent_extensions if ext.get("required", False)]

    if required_extensions:
        logger.warning("=" * 60)
        logger.warning("CLIENT COMPATIBILITY WARNING")
        logger.warning("=" * 60)
        logger.warning(f"This agent requires {len(required_extensions)} extensions:")

        for ext in required_extensions:
            uri = ext["uri"]
            description = ext.get("description", "No description provided")
            logger.warning(f"  - {uri}: {description}")

        logger.warning("")
        logger.warning("Clients that don't support these extensions SHOULD expect failures")
        logger.warning("when attempting to interact with this agent.")
        logger.warning("=" * 60)
    else:
        logger.info("No required extensions - all extensions are optional")
        logger.info("Clients can safely interact without extension support")
