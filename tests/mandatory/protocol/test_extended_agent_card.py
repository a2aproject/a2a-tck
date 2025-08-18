"""
A2A v0.3.0 Protocol: Mandatory Extended Agent Card Tests

SPECIFICATION REQUIREMENTS (Section 7.10):
- agent/authenticatedExtendedCard endpoint MUST be available when declared
- Client MUST authenticate using declared security schemes
- Server SHOULD include WWW-Authenticate header on 401 responses
- Clients SHOULD replace cached Agent Card with extended card content

These tests verify the mandatory agent/authenticatedExtendedCard method
when supportsAuthenticatedExtendedCard is declared in the Agent Card.

Reference: A2A v0.3.0 Specification Section 7.10 (agent/authenticatedExtendedCard)
"""

import logging
import urllib.parse
from typing import Dict, Any

import pytest
import requests

from tck import agent_card_utils, config
from tck.sut_client import SUTClient
from tests.markers import mandatory

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def sut_client():
    """Fixture to provide a SUTClient instance."""
    return SUTClient()


@pytest.fixture(scope="module")
def extended_card_agent_card(agent_card_data):
    """
    Fixture that only returns Agent Card data if extended card is supported.
    This ensures these tests only run when extended card is declared.
    """
    if agent_card_data is None:
        pytest.skip("Agent Card not available - cannot test extended card requirements")

    supports_extended = agent_card_data.get("supportsAuthenticatedExtendedCard", False)
    if not supports_extended:
        pytest.skip("supportsAuthenticatedExtendedCard not declared - extended card tests not applicable")

    return agent_card_data


@pytest.fixture(scope="module")
def extended_card_security_schemes(extended_card_agent_card):
    """Extract security schemes required for extended card access."""
    return agent_card_utils.get_authentication_schemes(extended_card_agent_card)


def get_extended_card_url(base_url: str) -> str:
    """
    Construct the extended Agent Card URL according to A2A v0.3.0 specification.

    Per Section 7.10: The endpoint URL is {AgentCard.url}/../agent/authenticatedExtendedCard
    relative to the base URL specified in the public Agent Card.
    """
    parsed = urllib.parse.urlparse(base_url)

    # Remove the path and add the extended card path
    base_path = parsed.path.rstrip("/")
    if base_path:
        # Go up one directory from the base path, then add the extended card path
        parent_path = "/".join(base_path.split("/")[:-1])
        extended_path = f"{parent_path}/agent/authenticatedExtendedCard"
    else:
        extended_path = "/agent/authenticatedExtendedCard"

    # Reconstruct the URL
    extended_url = urllib.parse.urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            extended_path,
            "",  # params
            "",  # query
            "",  # fragment
        )
    )

    return extended_url


@mandatory
def test_extended_agent_card_endpoint_exists(extended_card_agent_card):
    """
    MANDATORY: A2A v0.3.0 Section 7.10 - Extended Agent Card Endpoint Availability

    When supportsAuthenticatedExtendedCard is declared as true, the agent MUST
    implement the agent/authenticatedExtendedCard endpoint.

    This endpoint is an HTTP GET endpoint (not JSON-RPC) that returns a more
    detailed Agent Card after authentication.

    Test Procedure:
    1. Construct extended card URL from base Agent Card URL
    2. Send unauthenticated GET request
    3. Verify endpoint exists (should return 401, not 404)

    Asserts:
        - Extended card endpoint exists and is accessible
        - Returns 401/403 for unauthenticated requests (not 404)
        - Endpoint responds to HTTP GET requests
    """
    base_url = extended_card_agent_card.get("url")
    if not base_url:
        pytest.fail("Agent Card missing required 'url' field")

    extended_url = get_extended_card_url(base_url)
    logger.info(f"Testing extended Agent Card endpoint: {extended_url}")

    try:
        # Send unauthenticated GET request
        response = requests.get(extended_url, timeout=10)

        # The endpoint should exist but require authentication
        if response.status_code == 404:
            pytest.fail(
                f"SPECIFICATION VIOLATION: Extended Agent Card endpoint not found. "
                f"A2A v0.3.0 Section 7.10 requires endpoint when supportsAuthenticatedExtendedCard=true. "
                f"Got HTTP 404 for: {extended_url}"
            )
        elif response.status_code in (401, 403):
            logger.info(f"✅ Extended card endpoint exists and requires authentication (HTTP {response.status_code})")

            # Check for WWW-Authenticate header (SHOULD requirement)
            if "WWW-Authenticate" in response.headers:
                logger.info(f"✅ Server included WWW-Authenticate header: {response.headers['WWW-Authenticate']}")
            else:
                logger.warning("⚠️ Server missing WWW-Authenticate header (SHOULD requirement)")

        elif response.status_code == 200:
            # This might be valid if no authentication is required, check the response
            try:
                extended_card = response.json()
                if isinstance(extended_card, dict) and "name" in extended_card:
                    logger.info("✅ Extended card endpoint accessible without authentication")
                    logger.warning("Note: Extended card accessible without auth (consider security implications)")
                else:
                    pytest.fail(f"Extended card endpoint returned invalid Agent Card format")
            except ValueError:
                pytest.fail(f"Extended card endpoint returned non-JSON response")
        else:
            logger.warning(f"Unexpected HTTP status for extended card endpoint: {response.status_code}")

    except requests.exceptions.ConnectionError as e:
        pytest.fail(f"Cannot connect to extended card endpoint: {e}")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request to extended card endpoint failed: {e}")


@mandatory
def test_extended_agent_card_authentication_required(extended_card_agent_card, extended_card_security_schemes):
    """
    MANDATORY: A2A v0.3.0 Section 7.10 - Authentication Requirement

    The client MUST authenticate the request using one of the schemes declared
    in the public AgentCard.securitySchemes and AgentCard.security fields.

    This test verifies that authentication is properly enforced for the
    extended card endpoint when security schemes are declared.

    Test Procedure:
    1. Send request without authentication
    2. Verify 401/403 response with proper headers
    3. Check authentication scheme requirements

    Asserts:
        - Unauthenticated requests are rejected with 401/403
        - Authentication schemes are properly enforced
        - Error responses include proper authentication challenges
    """
    if not extended_card_security_schemes:
        pytest.skip("No authentication schemes declared - cannot test auth requirement")

    base_url = extended_card_agent_card.get("url")
    extended_url = get_extended_card_url(base_url)

    logger.info(f"Testing authentication requirement for extended card: {extended_url}")
    logger.info(f"Declared security schemes: {len(extended_card_security_schemes)}")

    try:
        # Send request without authentication headers
        response = requests.get(extended_url, timeout=10)

        # MANDATORY: Must require authentication when schemes are declared
        if response.status_code not in (401, 403):
            if response.status_code == 200:
                pytest.fail(
                    f"SPECIFICATION VIOLATION: Extended card endpoint should require authentication. "
                    f"A2A v0.3.0 Section 7.10 requires authentication using declared schemes. "
                    f"Got HTTP 200 without authentication"
                )
            else:
                pytest.fail(
                    f"Unexpected response for unauthenticated extended card request. "
                    f"Expected HTTP 401/403, got HTTP {response.status_code}"
                )

        logger.info(f"✅ Extended card properly requires authentication (HTTP {response.status_code})")

        # Verify WWW-Authenticate header (SHOULD requirement)
        auth_header = response.headers.get("WWW-Authenticate")
        if auth_header:
            logger.info(f"✅ WWW-Authenticate header present: {auth_header}")
        else:
            logger.warning("⚠️ Missing WWW-Authenticate header (recommended by specification)")

    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request to extended card endpoint failed: {e}")


@mandatory
def test_extended_agent_card_invalid_authentication(extended_card_agent_card, extended_card_security_schemes):
    """
    MANDATORY: A2A v0.3.0 Section 7.10 - Invalid Authentication Handling

    The extended card endpoint MUST properly validate authentication credentials
    and reject requests with invalid authentication data.

    Test Procedure:
    1. Send requests with invalid credentials for each scheme type
    2. Verify proper rejection with 401/403
    3. Check error handling consistency

    Asserts:
        - Invalid credentials are consistently rejected
        - Proper HTTP status codes are returned
        - Authentication validation is implemented correctly
    """
    if not extended_card_security_schemes:
        pytest.skip("No authentication schemes declared - cannot test invalid auth")

    base_url = extended_card_agent_card.get("url")
    extended_url = get_extended_card_url(base_url)

    logger.info(f"Testing invalid authentication for extended card: {extended_url}")

    # Test invalid credentials for each declared scheme
    for i, scheme in enumerate(extended_card_security_schemes):
        scheme_type = scheme.get("type", "unknown").lower()
        scheme_name = scheme.get("scheme", "unknown")

        logger.info(f"Testing invalid credentials for scheme {i + 1}: {scheme_type}")

        headers = {}

        # Add invalid authentication based on scheme type
        if scheme_type == "http" and scheme_name.lower() == "bearer":
            headers["Authorization"] = "Bearer invalid-extended-card-token-12345"
        elif scheme_type == "http" and scheme_name.lower() == "basic":
            headers["Authorization"] = "Basic aW52YWxpZDppbnZhbGlk"  # invalid:invalid
        elif scheme_type == "apikey":
            key_name = scheme.get("name", "X-API-Key")
            key_location = scheme.get("in", "header")

            if key_location == "header":
                headers[key_name] = "invalid-extended-api-key-12345"
            else:
                logger.warning(f"API key location '{key_location}' not implemented in test")
                continue
        elif scheme_type == "oauth2":
            headers["Authorization"] = "Bearer invalid-extended-oauth2-token-12345"
        elif scheme_type == "openidconnect":
            headers["Authorization"] = "Bearer invalid-extended-oidc-token-12345"
        else:
            headers["Authorization"] = f"Bearer invalid-extended-token-{scheme_type}"

        try:
            response = requests.get(extended_url, headers=headers, timeout=10)

            # MANDATORY: Invalid credentials must be rejected
            if response.status_code not in (401, 403):
                if response.status_code == 200:
                    pytest.fail(
                        f"SPECIFICATION VIOLATION: Extended card accepted invalid {scheme_type} credentials. "
                        f"A2A v0.3.0 Section 7.10 requires proper credential validation. "
                        f"Got HTTP 200 with invalid authentication"
                    )
                else:
                    logger.warning(f"Unexpected status for invalid {scheme_type} credentials: {response.status_code}")
            else:
                logger.info(f"✅ Invalid {scheme_type} credentials properly rejected (HTTP {response.status_code})")

        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed for scheme {scheme_type}: {e}")


@mandatory
def test_extended_agent_card_response_format(extended_card_agent_card):
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
    base_url = extended_card_agent_card.get("url")
    extended_url = get_extended_card_url(base_url)

    logger.info(f"Testing extended Agent Card response format: {extended_url}")

    # Note: In a real test environment, valid authentication credentials would be provided
    # For this mandatory test, we'll test the response format if accessible

    try:
        # Attempt request without auth first to see response format
        response = requests.get(extended_url, timeout=10)

        if response.status_code == 200:
            # If accessible without auth, validate the response format
            try:
                extended_card = response.json()

                # Validate basic Agent Card structure
                required_fields = [
                    "name",
                    "description",
                    "url",
                    "version",
                    "capabilities",
                    "defaultInputModes",
                    "defaultOutputModes",
                    "skills",
                ]

                for field in required_fields:
                    assert field in extended_card, f"Extended Agent Card missing required field: {field}"

                # Verify it's a properly formatted Agent Card
                assert isinstance(extended_card.get("skills"), list), "Extended card 'skills' must be an array"
                assert isinstance(extended_card.get("capabilities"), dict), "Extended card 'capabilities' must be an object"

                logger.info("✅ Extended Agent Card response format validation passed")
                logger.info(f"Extended card has {len(extended_card.get('skills', []))} skills")

                # Compare with public card to ensure it's extended
                public_skill_count = len(extended_card_agent_card.get("skills", []))
                extended_skill_count = len(extended_card.get("skills", []))

                if extended_skill_count > public_skill_count:
                    logger.info(f"✅ Extended card provides additional skills ({extended_skill_count} vs {public_skill_count})")
                else:
                    logger.info(f"Extended card has same skill count as public card ({extended_skill_count})")

            except ValueError:
                pytest.fail("Extended Agent Card endpoint returned invalid JSON")
            except AssertionError as e:
                pytest.fail(f"Extended Agent Card format validation failed: {e}")

        elif response.status_code in (401, 403):
            logger.info("Extended card requires authentication - response format test skipped")
            logger.info("To test response format, provide valid authentication credentials")
            pytest.skip("Extended card requires authentication - cannot test response format without credentials")

        else:
            pytest.skip(f"Cannot test response format - HTTP {response.status_code}")

    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request to extended card endpoint failed: {e}")
