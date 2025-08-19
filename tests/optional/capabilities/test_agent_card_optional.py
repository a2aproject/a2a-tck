"""
A2A Protocol Specification: Agent Card optional capabilities validation tests.

This test suite validates the optional capabilities structure of the SUT's Agent Card
according to the A2A specification: https://google.github.io/A2A/specification/#agent-card
"""

import logging
import re

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


@optional_capability
def test_capabilities_structure(fetched_agent_card):
    """
    OPTIONAL CAPABILITY: A2A Specification §5.5.2 - AgentCapabilities Structure

    While the capabilities field itself is MANDATORY, the specific
    capabilities (streaming, pushNotifications, extensions, etc.) are optional.
    This validates their structure if present.

    Failure Impact: Limits feature completeness (perfectly acceptable)
    Fix Suggestion: Implement optional capabilities to enhance functionality

    Asserts:
        - Capabilities object structure is valid if present
        - Individual capability values have correct types
        - Skills structure is valid if present
        - Extensions array structure is valid if present
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

    # Check stateTransitionHistory capability if present
    if "stateTransitionHistory" in capabilities:
        assert isinstance(capabilities["stateTransitionHistory"], bool), "stateTransitionHistory capability must be a boolean"

    # Check extensions array if present (NEW from spec update)
    if "extensions" in capabilities:
        extensions = capabilities["extensions"]
        assert isinstance(extensions, list), "extensions must be an array"

        # Validate each extension
        for i, extension in enumerate(extensions):
            assert isinstance(extension, dict), f"extension at index {i} must be an object"
            assert "uri" in extension, f"extension at index {i} missing required 'uri' field"
            assert isinstance(extension["uri"], str), f"extension uri at index {i} must be a string"

            # Check optional fields
            if "description" in extension:
                assert isinstance(extension["description"], str), f"extension description at index {i} must be a string"

            if "required" in extension:
                assert isinstance(extension["required"], bool), f"extension required at index {i} must be a boolean"

            if "params" in extension:
                assert isinstance(extension["params"], dict), f"extension params at index {i} must be an object"

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
def test_agent_extensions_structure(fetched_agent_card):
    """
    OPTIONAL CAPABILITY: A2A Specification §5.5.2.1 - AgentExtension Objects

    Tests the new AgentExtension capability structure introduced in the latest spec.
    Extensions allow agents to declare additional capabilities beyond the core protocol.

    Failure Impact: Limits extensibility features (perfectly acceptable)
    Fix Suggestion: Implement extension support to enable advanced capabilities

    Asserts:
        - Extensions array follows AgentExtension schema
        - Required 'uri' field is present and valid
        - Optional fields have correct types when present
        - Extension URIs are well-formed
    """
    # Skip if capabilities is not present
    if "capabilities" not in fetched_agent_card:
        pytest.skip("Agent Card does not have a capabilities section")

    capabilities = fetched_agent_card["capabilities"]

    # Skip if extensions is not present (it's optional)
    if "extensions" not in capabilities:
        pytest.skip("Agent Card capabilities do not include extensions")

    extensions = capabilities["extensions"]
    assert isinstance(extensions, list), "extensions must be an array"

    if not extensions:
        logger.info("Extensions array is empty (valid)")
        return

    # Validate each extension follows AgentExtension schema
    for i, extension in enumerate(extensions):
        assert isinstance(extension, dict), f"extension at index {i} must be an object"

        # Required field: uri
        assert "uri" in extension, f"extension at index {i} missing required 'uri' field"
        uri = extension["uri"]
        assert isinstance(uri, str), f"extension uri at index {i} must be a string"
        assert uri.strip(), f"extension uri at index {i} cannot be empty"

        # Optional field: description
        if "description" in extension:
            description = extension["description"]
            assert isinstance(description, str), f"extension description at index {i} must be a string"

        # Optional field: required
        if "required" in extension:
            required = extension["required"]
            assert isinstance(required, bool), f"extension required at index {i} must be a boolean"

            # Log information about required extensions for debugging
            if required:
                logger.info(f"Extension {uri} is marked as required by the agent")

        # Optional field: params
        if "params" in extension:
            params = extension["params"]
            assert isinstance(params, dict), f"extension params at index {i} must be an object"
            # params can contain any configuration, so we don't validate specific content

        logger.info(f"Validated extension {i}: {uri}")


@optional_capability
def test_authentication_structure(fetched_agent_card):
    """
    OPTIONAL CAPABILITY: A2A Specification §5.5.4 - Authentication Structure

    Authentication schemes are optional capabilities. This validates
    their structure if present, but does not require them.

    Failure Impact: Limits feature completeness (perfectly acceptable)
    Fix Suggestion: Implement authentication schemes to enable secure access

    Asserts:
        - Authentication array structure is valid if present
        - Individual authentication schemes have correct types
        - Known authentication scheme properties are properly structured
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


@optional_capability
def test_agent_interfaces_structure(fetched_agent_card):
    """
    OPTIONAL CAPABILITY: A2A Specification §5.5.5 - AgentInterface Objects

    Tests the additionalInterfaces field which contains AgentInterface objects.
    This allows agents to declare multiple transport endpoints for client flexibility.

    Failure Impact: Limits transport flexibility (perfectly acceptable)
    Fix Suggestion: Implement additional interfaces to support multiple transports

    Asserts:
        - additionalInterfaces array follows AgentInterface schema
        - Required 'url' and 'transport' fields are present and valid
        - Transport values are reasonable
        - URLs appear well-formed
    """
    # Skip if additionalInterfaces is not present (it's optional)
    if "additionalInterfaces" not in fetched_agent_card:
        pytest.skip("Agent Card does not include additionalInterfaces")

    interfaces = fetched_agent_card["additionalInterfaces"]
    assert isinstance(interfaces, list), "additionalInterfaces must be an array"

    if not interfaces:
        logger.info("additionalInterfaces array is empty (valid)")
        return

    # Validate each interface follows AgentInterface schema
    for i, interface in enumerate(interfaces):
        assert isinstance(interface, dict), f"interface at index {i} must be an object"

        # Required field: url
        assert "url" in interface, f"interface at index {i} missing required 'url' field"
        url = interface["url"]
        assert isinstance(url, str), f"interface url at index {i} must be a string"
        assert url.strip(), f"interface url at index {i} cannot be empty"

        # Basic URL format validation
        assert url.startswith(("http://", "https://")), f"interface url at index {i} must be a valid HTTP/HTTPS URL"

        # Required field: transport
        assert "transport" in interface, f"interface at index {i} missing required 'transport' field"
        transport = interface["transport"]
        assert isinstance(transport, str), f"interface transport at index {i} must be a string"
        assert transport.strip(), f"interface transport at index {i} cannot be empty"

        # Validate transport is one of the officially supported values (per spec: JSONRPC, GRPC, HTTP+JSON)
        # But allow other values as the spec says it's "open form string"
        known_transports = ["JSONRPC", "GRPC", "HTTP+JSON"]
        if transport in known_transports:
            logger.info(f"Interface {i} uses officially supported transport: {transport}")
        else:
            logger.info(f"Interface {i} uses custom transport: {transport}")

        logger.info(f"Validated interface {i}: {transport} at {url}")

    logger.info(f"Agent declares {len(interfaces)} additional interfaces")
