"""
A2A v0.3.0 Protocol: Mandatory Authentication Enforcement Tests

SPECIFICATION REQUIREMENTS (Section 4.3-4.4):
- "The A2A Server MUST authenticate every incoming request based on
   the provided HTTP credentials and its declared authentication requirements"
- "SHOULD use standard HTTP status codes like 401 Unauthorized or 403 Forbidden"
- "SHOULD include relevant HTTP headers (e.g., WWW-Authenticate)"

These tests verify that authentication is MANDATORY when declared in the Agent Card.
Unlike the optional authentication tests, these tests FAIL if authentication
is not properly enforced when required.

Reference: A2A v0.3.0 Specification Section 4 (Authentication and Authorization)
"""

import logging
import pytest
import requests

from tck import agent_card_utils, config, message_utils
from tck.sut_client import SUTClient
from tests.markers import mandatory

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def sut_client():
    """Fixture to provide a SUTClient instance."""
    return SUTClient()


@pytest.fixture(scope="module")
def auth_agent_card(agent_card_data):
    """
    Fixture that only returns Agent Card data if authentication is declared.
    This ensures these tests only run when authentication is a REQUIREMENT.
    """
    if agent_card_data is None:
        pytest.skip("Agent Card not available - cannot test authentication requirements")

    auth_schemes = agent_card_utils.get_authentication_schemes(agent_card_data)
    if not auth_schemes:
        pytest.skip("No authentication schemes declared in Agent Card - authentication tests not applicable")

    return agent_card_data


@pytest.fixture(scope="module")
def security_schemes(auth_agent_card):
    """Extract security schemes from Agent Card that declares authentication."""
    return agent_card_utils.get_authentication_schemes(auth_agent_card)


@mandatory
def test_authentication_required_when_declared(security_schemes):
    """
    MANDATORY: A2A v0.3.0 Section 4.4 - Authentication Enforcement

    When authentication schemes are declared in the Agent Card, the A2A Server
    MUST authenticate every incoming request. Requests without proper authentication
    MUST be rejected with appropriate HTTP status codes.

    This is a MANDATORY requirement - if authentication is declared, it MUST be enforced.

    Test Procedure:
    1. Send request without authentication headers
    2. Verify server returns HTTP 401 Unauthorized or 403 Forbidden
    3. Verify WWW-Authenticate header is included (SHOULD requirement)

    Asserts:
        - HTTP status code is 401 or 403 when auth is missing
        - WWW-Authenticate header is present (recommended)
        - Response follows A2A error format if JSON-RPC layer is reached
    """
    if not security_schemes:
        pytest.fail("Test should have been skipped - no authentication schemes found")

    logger.info(f"Testing authentication enforcement with {len(security_schemes)} declared schemes")

    # Create a direct session without any authentication
    session = requests.Session()

    # Prepare a simple JSON-RPC request
    req_id = message_utils.generate_request_id()
    params = {"id": f"test-task-{req_id}"}
    json_rpc_request = message_utils.make_json_rpc_request("tasks/get", params=params, id=req_id)

    # Send request without authentication headers
    sut_url = config.get_sut_url()
    headers = {"Content-Type": "application/json"}

    try:
        response = session.post(sut_url, json=json_rpc_request, headers=headers, timeout=10)

        # MANDATORY: Server MUST reject unauthenticated requests when auth is declared
        if response.status_code in (401, 403):
            logger.info(f"✅ Server correctly rejected unauthenticated request with HTTP {response.status_code}")

            # SHOULD requirement: Check for WWW-Authenticate header
            if "WWW-Authenticate" in response.headers:
                logger.info(f"✅ Server included WWW-Authenticate header: {response.headers['WWW-Authenticate']}")
            else:
                logger.warning("⚠️ Server missing WWW-Authenticate header (SHOULD requirement)")

        elif response.status_code == 200:
            # This is a specification violation - authentication is declared but not enforced
            try:
                json_response = response.json()
                if "error" in json_response:
                    error_code = json_response["error"].get("code")
                    error_message = json_response["error"].get("message", "")

                    # Check if it's an authentication-related JSON-RPC error
                    if error_code in (-32600, -32601, -32602, -32603) or any(
                        keyword in error_message.lower() for keyword in ["auth", "unauthorized", "forbidden"]
                    ):
                        pytest.fail(
                            f"SPECIFICATION VIOLATION: Server returned HTTP 200 with JSON-RPC error instead of HTTP 401/403. "
                            f"A2A v0.3.0 Section 4.4 requires HTTP-level authentication rejection. "
                            f"Got: {json_response['error']}"
                        )
                    else:
                        pytest.fail(
                            f"SPECIFICATION VIOLATION: Server processed unauthenticated request successfully. "
                            f"A2A v0.3.0 Section 4.4 REQUIRES authentication enforcement when schemes are declared. "
                            f"Expected HTTP 401/403, got HTTP 200 with non-auth error: {json_response['error']}"
                        )
                else:
                    # Successful response is a clear violation
                    pytest.fail(
                        f"SPECIFICATION VIOLATION: Server accepted unauthenticated request successfully. "
                        f"A2A v0.3.0 Section 4.4 REQUIRES authentication enforcement when schemes are declared. "
                        f"Expected HTTP 401/403, got HTTP 200 with success response"
                    )
            except ValueError:
                pytest.fail(
                    f"SPECIFICATION VIOLATION: Server returned HTTP 200 with non-JSON response to unauthenticated request. "
                    f"A2A v0.3.0 Section 4.4 REQUIRES authentication enforcement when schemes are declared. "
                    f"Expected HTTP 401/403"
                )
        else:
            pytest.fail(
                f"Unexpected HTTP status code for unauthenticated request. "
                f"Expected HTTP 401/403 per A2A v0.3.0 Section 4.4, got HTTP {response.status_code}"
            )

    except requests.RequestException as e:
        pytest.fail(f"Request failed with network error: {e}")


@mandatory
def test_invalid_credentials_rejected(security_schemes):
    """
    MANDATORY: A2A v0.3.0 Section 4.4 - Invalid Credential Handling

    When authentication schemes are declared, the A2A Server MUST properly validate
    credentials and reject requests with invalid authentication data.

    This is a MANDATORY requirement for security compliance.

    Test Procedure:
    1. Send request with invalid credentials for each declared scheme type
    2. Verify server returns HTTP 401 Unauthorized or 403 Forbidden
    3. Verify proper error handling and response format

    Asserts:
        - Invalid credentials are consistently rejected
        - HTTP status code is 401 or 403 for invalid auth
        - Security validation is properly implemented
    """
    if not security_schemes:
        pytest.fail("Test should have been skipped - no authentication schemes found")

    logger.info(f"Testing invalid credential rejection with {len(security_schemes)} declared schemes")

    # Test each declared authentication scheme
    for i, scheme in enumerate(security_schemes):
        scheme_type = scheme.get("type", "unknown").lower()
        scheme_name = scheme.get("scheme", "unknown")

        logger.info(f"Testing invalid credentials for scheme {i + 1}: {scheme_type}")

        # Create session with invalid credentials for this scheme type
        session = requests.Session()
        headers = {"Content-Type": "application/json"}

        # Add invalid authentication based on scheme type
        if scheme_type == "http" and scheme_name.lower() == "bearer":
            headers["Authorization"] = "Bearer invalid-dummy-jwt-token-12345"
        elif scheme_type == "http" and scheme_name.lower() == "basic":
            headers["Authorization"] = "Basic aW52YWxpZDppbnZhbGlk"  # invalid:invalid in base64
        elif scheme_type == "apikey":
            key_name = scheme.get("name", "X-API-Key")
            key_location = scheme.get("in", "header")

            if key_location == "header":
                headers[key_name] = "invalid-api-key-12345"
            else:
                # For query/cookie parameters, add to URL/cookies
                logger.warning(f"API key location '{key_location}' not implemented in test")
                continue
        elif scheme_type == "oauth2":
            headers["Authorization"] = "Bearer invalid-oauth2-token-12345"
        elif scheme_type == "openidconnect":
            headers["Authorization"] = "Bearer invalid-oidc-token-12345"
        else:
            # Generic fallback for unknown schemes
            headers["Authorization"] = f"Bearer invalid-token-for-{scheme_type}"

        # Prepare JSON-RPC request
        req_id = message_utils.generate_request_id()
        params = {"id": f"test-task-{req_id}-scheme-{i}"}
        json_rpc_request = message_utils.make_json_rpc_request("tasks/get", params=params, id=req_id)

        # Send request with invalid credentials
        sut_url = config.get_sut_url()

        try:
            response = session.post(sut_url, json=json_rpc_request, headers=headers, timeout=10)

            # MANDATORY: Server MUST reject invalid credentials
            if response.status_code in (401, 403):
                logger.info(f"✅ Server correctly rejected invalid {scheme_type} credentials with HTTP {response.status_code}")

            elif response.status_code == 200:
                # Check if JSON-RPC layer properly handled auth
                try:
                    json_response = response.json()
                    if "error" in json_response:
                        error_message = json_response["error"].get("message", "").lower()
                        if any(keyword in error_message for keyword in ["auth", "unauthorized", "forbidden", "invalid"]):
                            pytest.fail(
                                f"SPECIFICATION VIOLATION: Server returned HTTP 200 with JSON-RPC auth error for scheme '{scheme_type}'. "
                                f"A2A v0.3.0 Section 4.4 recommends HTTP 401/403 for authentication failures. "
                                f"Got: {json_response['error']}"
                            )
                        else:
                            pytest.fail(
                                f"SPECIFICATION VIOLATION: Invalid {scheme_type} credentials processed successfully. "
                                f"A2A v0.3.0 Section 4.4 REQUIRES credential validation. "
                                f"Expected auth rejection, got non-auth error: {json_response['error']}"
                            )
                    else:
                        pytest.fail(
                            f"SPECIFICATION VIOLATION: Invalid {scheme_type} credentials accepted successfully. "
                            f"A2A v0.3.0 Section 4.4 REQUIRES credential validation when schemes are declared. "
                            f"Expected HTTP 401/403, got HTTP 200 success"
                        )
                except ValueError:
                    pytest.fail(
                        f"SPECIFICATION VIOLATION: Invalid {scheme_type} credentials returned non-JSON response. "
                        f"A2A v0.3.0 Section 4.4 REQUIRES credential validation. "
                        f"Expected HTTP 401/403"
                    )
            else:
                pytest.fail(
                    f"Unexpected HTTP status code for invalid {scheme_type} credentials. "
                    f"Expected HTTP 401/403 per A2A v0.3.0 Section 4.4, got HTTP {response.status_code}"
                )

        except requests.RequestException as e:
            pytest.fail(f"Request failed with network error for scheme {scheme_type}: {e}")


@mandatory
def test_authentication_scheme_consistency(security_schemes, auth_agent_card):
    """
    MANDATORY: A2A v0.3.0 Section 5.5 - Authentication Scheme Declaration Consistency

    The authentication schemes declared in the Agent Card MUST be properly structured
    and contain all required fields according to the A2A specification.

    This ensures that clients can properly discover and implement the required
    authentication methods.

    Test Procedure:
    1. Validate each declared security scheme structure
    2. Verify required fields are present
    3. Check scheme types are recognized and valid

    Asserts:
        - All declared schemes have required fields
        - Scheme types are valid according to specification
        - Security requirements are properly formatted
    """
    if not security_schemes:
        pytest.fail("Test should have been skipped - no authentication schemes found")

    logger.info(f"Validating authentication scheme consistency for {len(security_schemes)} schemes")

    # Validate each security scheme structure
    for i, scheme in enumerate(security_schemes):
        scheme_name = f"Scheme {i + 1}"

        # Required field: type
        assert "type" in scheme, f"{scheme_name}: Missing required 'type' field"
        scheme_type = scheme["type"]

        # Validate known scheme types according to A2A v0.3.0 specification
        valid_types = ["http", "apiKey", "oauth2", "openIdConnect", "mutualTLS"]
        assert scheme_type in valid_types, f"{scheme_name}: Invalid scheme type '{scheme_type}'. Must be one of: {valid_types}"

        # Type-specific validation
        if scheme_type == "http":
            assert "scheme" in scheme, f"{scheme_name}: HTTP auth missing required 'scheme' field"
            http_scheme = scheme["scheme"].lower()
            valid_http_schemes = ["basic", "bearer", "digest"]
            assert http_scheme in valid_http_schemes, f"{scheme_name}: Invalid HTTP scheme '{http_scheme}'"

        elif scheme_type == "apiKey":
            assert "name" in scheme, f"{scheme_name}: API key auth missing required 'name' field"
            assert "in" in scheme, f"{scheme_name}: API key auth missing required 'in' field"

            key_location = scheme["in"]
            valid_locations = ["query", "header", "cookie"]
            assert key_location in valid_locations, f"{scheme_name}: Invalid API key location '{key_location}'"

        elif scheme_type == "oauth2":
            assert "flows" in scheme, f"{scheme_name}: OAuth2 auth missing required 'flows' field"
            flows = scheme["flows"]
            assert isinstance(flows, dict), f"{scheme_name}: OAuth2 'flows' must be an object"

        elif scheme_type == "openIdConnect":
            assert "openIdConnectUrl" in scheme, f"{scheme_name}: OpenID Connect missing required 'openIdConnectUrl' field"
            oidc_url = scheme["openIdConnectUrl"]
            assert oidc_url.startswith("https://"), f"{scheme_name}: OpenID Connect URL must use HTTPS"

        logger.info(f"✅ {scheme_name} ({scheme_type}) validation passed")

    # Validate security requirements in Agent Card
    if "security" in auth_agent_card:
        security_requirements = auth_agent_card["security"]
        assert isinstance(security_requirements, list), "Agent Card 'security' field must be an array"

        for req_i, requirement in enumerate(security_requirements):
            assert isinstance(requirement, dict), f"Security requirement {req_i + 1} must be an object"

            # Each requirement should reference declared schemes
            for scheme_name in requirement.keys():
                scheme_declared = any(
                    declared_name == scheme_name for declared_name in (auth_agent_card.get("securitySchemes", {})).keys()
                )
                assert scheme_declared, f"Security requirement references undeclared scheme '{scheme_name}'"

        logger.info(f"✅ Security requirements validation passed for {len(security_requirements)} requirements")
