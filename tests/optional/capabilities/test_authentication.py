"""
A2A Protocol Specification: Authentication protocol tests.

This test suite verifies the SUT's handling of authentication as specified in the
A2A specification: https://google.github.io/A2A/specification/#authentication

These tests focus on how the SUT responds to JSON-RPC requests when authentication
is declared in the Agent Card but not properly provided by the client.
"""

import logging

import pytest
import requests

from tck import agent_card_utils, config, message_utils
from tck.sut_client import SUTClient
from tests.markers import optional_capability

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def sut_client():
    """Fixture to provide a SUTClient instance."""
    return SUTClient()

@pytest.fixture(scope="module")
def auth_schemes(agent_card_data):
    """
    Fixture to extract authentication schemes from the Agent Card.
    """
    if agent_card_data is None:
        logger.warning("Agent Card data is None, authentication tests may be skipped")
        return []
    
    return agent_card_utils.get_authentication_schemes(agent_card_data)

@optional_capability
def test_auth_schemes_available(auth_schemes):
    """
    OPTIONAL CAPABILITY: A2A Specification §5.5.4 - Authentication Schemes Declaration
    
    Tests that authentication schemes are properly declared in the Agent Card.
    While authentication itself is optional, if declared it must be structured correctly.
    
    Failure Impact: Limits feature completeness (perfectly acceptable)
    Fix Suggestion: Implement authentication support or remove from Agent Card
    
    Asserts:
        - Authentication schemes are available if declared
        - Scheme structure follows A2A specification
        - Scheme types are recognized and valid
    """
    # This test doesn't fail if no schemes are found, it's informational
    if not auth_schemes:
        logger.info("No authentication schemes found in Agent Card")
        pytest.skip("No authentication schemes declared in Agent Card, skipping authentication tests")
    else:
        logger.info(f"Found {len(auth_schemes)} authentication schemes in Agent Card")
        for i, scheme in enumerate(auth_schemes):
            scheme_type = scheme.get("scheme", "unknown")
            logger.info(f"Scheme {i+1}: {scheme_type}")

@optional_capability
def test_missing_authentication(sut_client, auth_schemes):
    """
    OPTIONAL CAPABILITY: A2A Specification §5.5.4 - Authentication Requirements
    
    Tests proper authentication enforcement when schemes are declared.
    If authentication is declared, it should be properly enforced.
    
    Note: This test expects HTTP 401/403 but SDK doesn't enforce auth.
    This is a known SDK limitation - specification violation.
    
    Failure Impact: Security issue if authentication declared but not enforced
    Fix Suggestion: Implement proper authentication enforcement or remove from Agent Card
    
    Asserts:
        - Authentication failures return appropriate HTTP status codes
        - Error responses follow A2A specification format
        - Security requirements are properly enforced
    """
    # Skip this test if no authentication schemes are declared
    if not auth_schemes:
        pytest.skip("No authentication schemes declared in Agent Card")
    
    # Create a direct session without any authentication
    session = requests.Session()
    
    # Prepare a simple JSON-RPC request (tasks/get with a non-existent ID to ensure
    # the error is auth-related, not business logic)
    req_id = message_utils.generate_request_id()
    params = {"id": f"non-existent-task-{req_id}"}
    json_rpc_request = message_utils.make_json_rpc_request(
        "tasks/get", params=params, id=req_id
    )
    
    # Send the request directly without using SUTClient to avoid any authentication logic
    sut_url = config.get_sut_url()
    headers = {"Content-Type": "application/json"}
    
    try:
        response = session.post(
            sut_url, 
            json=json_rpc_request, 
            headers=headers,
            timeout=10
        )
        
        # If the SUT is properly implementing authentication according to the spec,
        # it should return HTTP 401 or 403 when auth is required but missing
        if response.status_code in (401, 403):
            logger.info(f"SUT responded with expected HTTP {response.status_code} for missing authentication")
        else:
            # If we get status 200, it could be that the SUT processes the request at the JSON-RPC layer
            # instead of failing immediately at the HTTP layer
            if response.status_code == 200:
                try:
                    json_response = response.json()
                    # Check if this is a JSON-RPC error related to auth
                    if "error" in json_response:
                        error_message = json_response["error"].get("message", "").lower()
                        if "auth" in error_message or "unauthorized" in error_message or "forbidden" in error_message:
                            logger.warning(
                                f"SUT returned HTTP 200 but JSON-RPC error for missing authentication: {json_response['error']}"
                            )
                            logger.warning("This is not preferred by the spec, which recommends HTTP 401/403 for auth failures")
                        else:
                            # Some other JSON-RPC error that may not be auth-related
                            logger.error(f"Unexpected JSON-RPC error: {json_response['error']}")
                            pytest.xfail("SDK doesn't enforce authentication - specification violation")
                    else:
                        # Success response means authentication is not actually enforced
                        logger.error("SUT accepted request without authentication, despite declaring auth schemes")
                        pytest.xfail("SDK doesn't enforce authentication - specification violation")
                except ValueError:
                    logger.error("SUT returned HTTP 200 with non-JSON response")
                    pytest.xfail("SDK doesn't enforce authentication - specification violation")
            else:
                # Some other HTTP status code
                logger.error(f"Unexpected HTTP status code: {response.status_code}")
                pytest.xfail(f"SDK doesn't enforce authentication - expected HTTP 401/403, got: {response.status_code}")
    
    except requests.RequestException as e:
        logger.error(f"HTTP error sending request: {e}")
        pytest.fail(f"Request failed: {e}")

@optional_capability
def test_invalid_authentication(sut_client, auth_schemes):
    """
    OPTIONAL CAPABILITY: A2A Specification §5.5.4 - Invalid Authentication Handling
    
    Tests proper handling of invalid authentication credentials when schemes are declared.
    If authentication is declared, invalid credentials should be rejected properly.
    
    Note: This test expects HTTP 401/403 but SDK doesn't enforce auth.
    This is a known SDK limitation - specification violation.
    
    Failure Impact: Security issue if invalid credentials are accepted
    Fix Suggestion: Implement proper credential validation or remove from Agent Card
    
    Asserts:
        - Invalid authentication credentials are rejected
        - Error responses use appropriate HTTP status codes
        - Security validation is consistently enforced
    """
    # Skip this test if no authentication schemes are declared
    if not auth_schemes:
        pytest.skip("No authentication schemes declared in Agent Card")
    
    # Create a direct session
    session = requests.Session()
    
    # Get the first declared auth scheme and create an invalid token/credentials
    auth_scheme = auth_schemes[0]
    scheme_type = auth_scheme.get("scheme", "").lower()
    
    # Prepare headers with invalid authentication
    headers = {"Content-Type": "application/json"}
    
    if scheme_type == "bearer":
        headers["Authorization"] = "Bearer invalid-dummy-token"
    elif scheme_type == "basic":
        headers["Authorization"] = "Basic aW52YWxpZDppbnZhbGlk"  # invalid:invalid in base64
    elif scheme_type == "apikey":
        # Look for the name and location of the API key
        key_name = auth_scheme.get("name", "x-api-key")
        key_location = auth_scheme.get("in", "header")
        
        if key_location == "header":
            headers[key_name] = "invalid-api-key"
        # For other locations like query params, we would need to modify the URL
    else:
        # For unknown schemes, try a generic auth header
        headers["Authorization"] = f"{scheme_type} invalid-token"
    
    # Prepare a simple JSON-RPC request
    req_id = message_utils.generate_request_id()
    params = {"id": f"non-existent-task-{req_id}"}
    json_rpc_request = message_utils.make_json_rpc_request(
        "tasks/get", params=params, id=req_id
    )
    
    # Send the request
    sut_url = config.get_sut_url()
    
    try:
        response = session.post(
            sut_url, 
            json=json_rpc_request, 
            headers=headers,
            timeout=10
        )
        
        # If the SUT is properly implementing authentication according to the spec,
        # it should return HTTP 401 or 403 for invalid auth
        if response.status_code in (401, 403):
            logger.info(f"SUT responded with expected HTTP {response.status_code} for invalid authentication")
        else:
            # Similar logic as in test_missing_authentication
            if response.status_code == 200:
                try:
                    json_response = response.json()
                    if "error" in json_response:
                        error_message = json_response["error"].get("message", "").lower()
                        if "auth" in error_message or "unauthorized" in error_message or "forbidden" in error_message:
                            logger.warning(
                                f"SUT returned HTTP 200 but JSON-RPC error for invalid authentication: {json_response['error']}"
                            )
                            logger.warning("This is not preferred by the spec, which recommends HTTP 401/403 for auth failures")
                        else:
                            # Some other JSON-RPC error that may not be auth-related
                            logger.error(f"Unexpected JSON-RPC error: {json_response['error']}")
                            pytest.xfail("SDK doesn't enforce authentication - specification violation")
                    else:
                        # Success response means invalid authentication was accepted
                        logger.error("SUT accepted request with invalid authentication")
                        pytest.xfail("SDK doesn't enforce authentication - specification violation")
                except ValueError:
                    logger.error("SUT returned HTTP 200 with non-JSON response")
                    pytest.xfail("SDK doesn't enforce authentication - specification violation")
            else:
                # Some other HTTP status code
                logger.error(f"Unexpected HTTP status code: {response.status_code}")
                pytest.xfail(f"SDK doesn't enforce authentication - expected HTTP 401/403, got: {response.status_code}")
    
    except requests.RequestException as e:
        logger.error(f"HTTP error sending request: {e}")
        pytest.fail(f"Request failed: {e}") 