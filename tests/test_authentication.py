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

def test_auth_schemes_available(auth_schemes):
    """
    Test that authentication schemes are available in the Agent Card.
    
    This is a preliminary test to determine if the SUT declares any authentication
    requirements. If not, the other authentication tests will be skipped.
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

def test_missing_authentication(sut_client, auth_schemes):
    """
    A2A Protocol Specification: Authentication - Server Response to Missing Authentication
    https://google.github.io/A2A/specification/#authentication
    
    Test the SUT's response when authentication is required but not provided.
    
    According to the A2A spec: "Servers SHOULD use HTTP 401 or 403 status codes for 
    authentication/authorization failures before the JSON-RPC layer is even reached."
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
                            pytest.fail(f"Expected HTTP 401/403 or auth-related JSON-RPC error, got: {json_response}")
                    else:
                        # Success response means authentication is not actually enforced
                        logger.error("SUT accepted request without authentication, despite declaring auth schemes")
                        pytest.fail("SUT accepted request without authentication")
                except ValueError:
                    logger.error("SUT returned HTTP 200 with non-JSON response")
                    pytest.fail(f"Expected JSON response or HTTP 401/403, got non-JSON with HTTP {response.status_code}")
            else:
                # Some other HTTP status code
                logger.error(f"Unexpected HTTP status code: {response.status_code}")
                pytest.fail(f"Expected HTTP 401/403, got: {response.status_code}")
    
    except requests.RequestException as e:
        logger.error(f"HTTP error sending request: {e}")
        pytest.fail(f"Request failed: {e}")

def test_invalid_authentication(sut_client, auth_schemes):
    """
    A2A Protocol Specification: Authentication - Server Response to Invalid Authentication
    https://google.github.io/A2A/specification/#authentication
    
    Test the SUT's response when invalid authentication is provided.
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
                            pytest.fail(f"Expected HTTP 401/403 or auth-related JSON-RPC error, got: {json_response}")
                    else:
                        # Success response means invalid authentication was accepted
                        logger.error("SUT accepted request with invalid authentication")
                        pytest.fail("SUT accepted request with invalid authentication")
                except ValueError:
                    logger.error("SUT returned HTTP 200 with non-JSON response")
                    pytest.fail(f"Expected JSON response or HTTP 401/403, got non-JSON with HTTP {response.status_code}")
            else:
                # Some other HTTP status code
                logger.error(f"Unexpected HTTP status code: {response.status_code}")
                pytest.fail(f"Expected HTTP 401/403, got: {response.status_code}")
    
    except requests.RequestException as e:
        logger.error(f"HTTP error sending request: {e}")
        pytest.fail(f"Request failed: {e}") 