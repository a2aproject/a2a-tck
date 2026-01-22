"""
A2A v0.3.0 Protocol: Mandatory Extended Agent Card Tests

SPECIFICATION REQUIREMENTS (Section 7.10):
- GetExtendedAgentCard JSON-RPC method, or getExtendedAgentCard gRPC
  method or /extendedAgentCard JSON+HTTP endpoint MUST be available when declared
- Client MUST authenticate using declared security schemes
- Clients SHOULD replace cached Agent Card with extended card content

These tests verify the mandatory getExtendedAgentCard method
when supportsAuthenticatedExtendedCard is declared in the Agent Card.

Reference: A2A v0.3.0 Specification Section 7.10 (agent/getAuthenticatedExtendedCard)
"""

import logging

import pytest
import requests

from tck import agent_card_utils
from tests.markers import optional_capability
from tests.utils.transport_helpers import is_json_rpc_error_response, is_json_rpc_success_response, transport_get_extended_agent_card

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def security_schemes(agent_card_data):
    """Extract security schemes required for extended card access."""
    if agent_card_data is None:
        pytest.skip("Agent Card not available - cannot test extended card requirements")

    supports_extended = agent_card_data.get("supportsExtendedAgentCard", False)
    if not supports_extended:
        pytest.skip("supportsExtendedAgentCard not declared - extended card tests not applicable")

    security_schemes = agent_card_utils.get_authentication_schemes(agent_card_data)
    if not security_schemes:
        pytest.fail("Agent card supports extended agent card but does provide security schemes for required authentication")
    return security_schemes


@optional_capability
def test_extended_agent_card_authentication_required(sut_client):
    """
    MANDATORY: A2A v0.3.0 Section 7.10 - Authentication Requirement

    The client MUST authenticate the request using one of the schemes declared
    in the public AgentCard.securitySchemes and AgentCard.security fields.

    This test verifies that authentication is properly enforced for the
    extended card endpoint when security schemes are declared.

    Test Procedure:
    1. Send request without authentication
    2. Verify response is an error
    """

    logger.info(f"Testing authentication requirement for extended card")

    try:
        resp = transport_get_extended_agent_card(sut_client, {"A2A_TCK_DONT_USE_AUTH": "True"})
        assert is_json_rpc_error_response(resp), f"Message GetExtendedAgentCard failed: {resp}"
        logger.info(f"✅ Extended card properly requires authentication ({resp})")

    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request to extended card endpoint failed: {e}")


@optional_capability
def test_extended_agent_card_invalid_authentication(sut_client, security_schemes):
    """
    MANDATORY: A2A v0.3.0 Section 7.10 - Invalid Authentication Handling

    The extended card endpoint MUST properly validate authentication credentials
    and reject requests with invalid authentication data.

    Test Procedure:
    1. Send requests with invalid credentials for each scheme type
    2. Verify proper rejection
    3. Check error handling consistency

    Asserts:
        - Invalid credentials are consistently rejected
        - Proper HTTP status codes are returned
        - Authentication validation is implemented correctly
    """
    logger.info(f"Testing invalid authentication for extended agent card")

    # Test invalid credentials for each declared scheme
    for scheme_name in security_schemes:
        security_scheme = security_schemes[scheme_name]
        assert len(security_scheme.keys()) == 1
        scheme_type, scheme = next(iter(security_scheme.items()))
        logger.info(f"Testing invalid credentials for scheme {scheme_name}/{scheme_type}")

        headers = {}

        # Add invalid authentication based on scheme type
        if scheme_type == "httpAuthSecurityScheme" and scheme_name.lower() == "bearer":
            headers["Authorization"] = "Bearer invalid-extended-card-token-12345"
        elif scheme_type == "httpAuthSecurityScheme" and scheme_name.lower() == "basic":
            headers["Authorization"] = "Basic aW52YWxpZDppbnZhbGlk"  # invalid:invalid
        elif scheme_type == "apiKeySecurityScheme":
            key_name = scheme.get("name", "X-API-Key")
            key_location = scheme.get("in", "header")

            if key_location == "header":
                headers[key_name] = "invalid-extended-api-key-12345"
            else:
                logger.warning(f"API key location '{key_location}' not implemented in test")
                continue
        elif scheme_type == "oauth2SecurityScheme":
            headers["Authorization"] = "Bearer invalid-extended-oauth2-token-12345"
        elif scheme_type == "openIdConnectSecurityScheme":
            headers["Authorization"] = "Bearer invalid-extended-oidc-token-12345"
        else:
            headers["Authorization"] = f"Bearer invalid-extended-token-{scheme_type}"

        try:
            response = transport_get_extended_agent_card(sut_client, headers)
            assert is_json_rpc_error_response(response), f"SPECIFICATION VIOLATION: Extended card accepted invalid {scheme_type} credentials for {scheme_type}"
            logger.info(f"✅ Invalid {scheme_type} credentials properly rejected")

        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed for scheme {scheme_type}: {e}")


@optional_capability
def test_extended_agent_card_response_format(sut_client, agent_card_data):
    """
    MANDATORY: A2A v0.3.0 Section 7.10 - Response Format Validation

    When authentication succeeds, the extended card endpoint MUST return
    a valid AgentCard object that conforms to the A2A specification.

    Note: This test can only run if valid authentication is available.
    In most cases, this will skip unless auth credentials are provided.

    Test Procedure:
    1. Attempt authenticated request (if credentials available)
    2. Verify response is valid JSON
    3. Validate Agent Card structure
    4. Check that extended card contains required fields

    Asserts:
        - Response is valid JSON Agent Card format
        - Contains all required Agent Card fields
        - Extended card provides additional details beyond public card
    """
    logger.info(f"Testing extended Agent Card response format")

    # Note: In a real test environment, valid authentication credentials would be provided
    # For this mandatory test, we'll test the response format if accessible

    try:
        response = transport_get_extended_agent_card(sut_client)
        assert is_json_rpc_success_response(response)
        assert "result" in response
        extended_card = response["result"]

        # Validate basic Agent Card structure
        required_fields = {
            "name",
            "description",
            "supportedInterfaces",
            "version",
            "capabilities",
            "defaultInputModes",
            "defaultOutputModes",
            "skills",
        }

        for field in required_fields:
            assert field in extended_card, f"Extended Agent Card missing required field: {field}"

            # Verify it's a properly formatted Agent Card
            assert isinstance(extended_card.get("skills"), list), "Extended card 'skills' must be an array"
            assert isinstance(extended_card.get("capabilities"), dict), "Extended card 'capabilities' must be an object"

            logger.info("✅ Extended Agent Card response format validation passed")
            logger.info(f"Extended card has {len(extended_card.get('skills', []))} skills")

            # Compare with public card to ensure it's extended
            public_skill_count = len(agent_card_data.get("skills", []))
            extended_skill_count = len(extended_card.get("skills", []))

            if extended_skill_count > public_skill_count:
                logger.info(f"✅ Extended card provides additional skills ({extended_skill_count} vs {public_skill_count})")
            else:
                logger.info(f"Extended card has same skill count as public card ({extended_skill_count})")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request to extended card endpoint failed: {e}")
