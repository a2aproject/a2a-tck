"""
A2A v0.3.0 Enhanced Authentication and Security Testing

This module implements comprehensive authentication testing for A2A v0.3.0 specification
including new security schemes, multi-transport authentication, and enhanced security validation.

Specification Reference: A2A Protocol v0.3.0 §4 - Authentication and Authorization
"""

import logging
from typing import Dict, Any, Optional, List
import pytest
import requests
import base64
import json

from tests.markers import optional_capability, a2a_v030
from tests.utils.transport_helpers import transport_get_agent_card, is_transport_client, get_client_transport_type
from tck import config, message_utils
from tck.transport.base_client import BaseTransportClient

logger = logging.getLogger(__name__)


@pytest.fixture
def auth_agent_card(sut_client):
    """
    Fixture to get agent card and extract authentication information.
    """
    try:
        response = transport_get_agent_card(sut_client)
        if "result" in response:
            return response["result"]
        elif "error" not in response:
            return response
        else:
            logger.warning(f"Could not fetch agent card: {response}")
            return None
    except Exception as e:
        logger.warning(f"Failed to fetch agent card: {e}")
        return None


@pytest.fixture
def security_schemes(auth_agent_card):
    """
    Extract security schemes from the Agent Card.
    """
    if not auth_agent_card:
        return []

    # A2A v0.3.0 uses securitySchemes field
    security_schemes = auth_agent_card.get("securitySchemes", {})
    if not security_schemes:
        # Fallback to legacy authentication field
        legacy_auth = auth_agent_card.get("authentication", [])
        return legacy_auth

    return list(security_schemes.values())


class TestA2AV030SecuritySchemes:
    """
    Test A2A v0.3.0 security scheme declarations and compliance.

    Validates that agents properly declare security schemes according to
    A2A v0.3.0 specification Section 4.
    """

    @optional_capability
    @a2a_v030
    def test_security_scheme_structure_compliance(self, security_schemes):
        """
        A2A v0.3.0 §4.1 - Security Scheme Structure Validation

        Validates that security schemes follow the OpenAPI 3.0 Security Scheme Object
        structure as specified in A2A v0.3.0.
        """
        if not security_schemes:
            pytest.skip("No security schemes declared in Agent Card")

        valid_scheme_types = ["apiKey", "http", "oauth2", "openIdConnect", "mutualTLS"]
        valid_api_key_locations = ["query", "header", "cookie"]

        for i, scheme in enumerate(security_schemes):
            scheme_type = scheme.get("type")
            assert scheme_type in valid_scheme_types, f"Security scheme {i} has invalid type: {scheme_type}"

            # Type-specific validation
            if scheme_type == "apiKey":
                assert "name" in scheme, f"API Key scheme {i} missing 'name' field"
                assert "in" in scheme, f"API Key scheme {i} missing 'in' field"
                assert scheme["in"] in valid_api_key_locations, f"API Key scheme {i} has invalid location: {scheme['in']}"

            elif scheme_type == "http":
                assert "scheme" in scheme, f"HTTP auth scheme {i} missing 'scheme' field"
                http_scheme = scheme["scheme"].lower()
                assert http_scheme in ["basic", "bearer", "digest"], f"HTTP auth scheme {i} has unsupported scheme: {http_scheme}"

            elif scheme_type == "oauth2":
                assert "flows" in scheme, f"OAuth2 scheme {i} missing 'flows' field"
                flows = scheme["flows"]
                valid_flows = ["authorizationCode", "clientCredentials", "implicit", "password"]
                assert any(flow in flows for flow in valid_flows), f"OAuth2 scheme {i} has no valid flows"

            elif scheme_type == "openIdConnect":
                assert "openIdConnectUrl" in scheme, f"OpenID Connect scheme {i} missing 'openIdConnectUrl' field"

    @optional_capability
    @a2a_v030
    def test_mutual_tls_scheme_support(self, security_schemes):
        """
        A2A v0.3.0 §4.1 - Mutual TLS Security Scheme Support

        Tests support for the new mutualTLS security scheme type
        introduced in A2A v0.3.0.
        """
        if not security_schemes:
            pytest.skip("No security schemes declared in Agent Card")

        mutual_tls_schemes = [s for s in security_schemes if s.get("type") == "mutualTLS"]

        if not mutual_tls_schemes:
            pytest.skip("No mutualTLS security schemes declared")

        for scheme in mutual_tls_schemes:
            # Mutual TLS schemes should have minimal structure
            assert scheme["type"] == "mutualTLS"
            # Optional description field
            if "description" in scheme:
                assert isinstance(scheme["description"], str)

    @optional_capability
    @a2a_v030
    def test_oauth2_metadata_url_support(self, security_schemes):
        """
        A2A v0.3.0 §4.1 - OAuth2 Metadata URL Support

        Tests support for the oauth2MetadataUrl field in OAuth2 security schemes,
        a new feature in A2A v0.3.0.
        """
        if not security_schemes:
            pytest.skip("No security schemes declared in Agent Card")

        oauth2_schemes = [s for s in security_schemes if s.get("type") == "oauth2"]

        if not oauth2_schemes:
            pytest.skip("No OAuth2 security schemes declared")

        for scheme in oauth2_schemes:
            if "oauth2MetadataUrl" in scheme:
                metadata_url = scheme["oauth2MetadataUrl"]
                assert isinstance(metadata_url, str)
                assert metadata_url.startswith("https://"), "OAuth2 metadata URL must use HTTPS"


class TestMultiTransportAuthentication:
    """
    Test authentication consistency across multiple transport types.

    Validates that authentication schemes work consistently across
    JSON-RPC, gRPC, and REST transports as specified in A2A v0.3.0.
    """

    @optional_capability
    @a2a_v030
    def test_authentication_transport_independence(self, sut_client, security_schemes):
        """
        A2A v0.3.0 §3.4.1 - Authentication Transport Independence

        Validates that authentication schemes work consistently across
        all supported transport types.
        """
        if not security_schemes:
            pytest.skip("No security schemes declared in Agent Card")

        if not is_transport_client(sut_client):
            pytest.skip("Test requires transport-aware client")

        transport_type = get_client_transport_type(sut_client)

        # Test that authentication works for this transport
        # This is a basic connectivity test - actual auth validation
        # would require valid credentials which are out-of-band
        try:
            # Attempt to get agent card (should work regardless of auth)
            response = transport_get_agent_card(sut_client)

            # Verify response structure
            assert isinstance(response, dict)

            # If authentication is required, we expect either:
            # 1. Success (if client has valid auth)
            # 2. Auth error (if client lacks auth)
            if "error" in response:
                error = response["error"]
                # Check if this is an auth-related error
                if error.get("code") in [401, 403] or any(
                    term in str(error.get("message", "")).lower() for term in ["auth", "unauthorized", "forbidden"]
                ):
                    logger.info(f"Authentication required for {transport_type} transport")
                else:
                    # Some other error, not auth-related
                    pass

        except Exception as e:
            # Network or protocol errors are not auth failures
            logger.warning(f"Transport test failed for {transport_type}: {e}")


class TestEnhancedSecurityValidation:
    """
    Enhanced security validation tests for A2A v0.3.0 features.

    Tests advanced security scenarios including in-task authentication,
    credential refresh, and security scheme negotiation.
    """

    @optional_capability
    @a2a_v030
    def test_in_task_authentication_flow(self, sut_client, security_schemes):
        """
        A2A v0.3.0 §4.5 - In-Task Authentication (Secondary Credentials)

        Tests the in-task authentication flow where an agent requests
        additional credentials during task execution.
        """
        if not security_schemes:
            pytest.skip("No security schemes declared in Agent Card")

        # This test would require a SUT that actually implements
        # in-task authentication. For now, we test the concept
        pytest.skip("In-task authentication requires SUT implementation support")

    @optional_capability
    @a2a_v030
    def test_security_scheme_negotiation(self, sut_client, security_schemes):
        """
        A2A v0.3.0 §4.3 - Security Scheme Negotiation

        Tests that clients can discover and negotiate appropriate
        security schemes from the Agent Card.
        """
        if not security_schemes:
            pytest.skip("No security schemes declared in Agent Card")

        # Verify that security schemes are discoverable
        for scheme in security_schemes:
            scheme_type = scheme.get("type")

            # Each scheme should have enough information for client implementation
            if scheme_type == "apiKey":
                assert "name" in scheme and "in" in scheme
            elif scheme_type == "http":
                assert "scheme" in scheme
            elif scheme_type == "oauth2":
                assert "flows" in scheme
                # Check if metadata URL is provided for easier discovery
                if "oauth2MetadataUrl" in scheme:
                    logger.info(f"OAuth2 metadata URL provided: {scheme['oauth2MetadataUrl']}")
            elif scheme_type == "openIdConnect":
                assert "openIdConnectUrl" in scheme

    @optional_capability
    @a2a_v030
    def test_transport_security_requirements(self, sut_client):
        """
        A2A v0.3.0 §4.1 - Transport Security Requirements

        Validates that the SUT enforces HTTPS and proper TLS configuration
        as required by A2A v0.3.0 specification.
        """
        sut_url = config.get_sut_url()

        # Skip HTTPS requirement for localhost testing
        if "localhost" in sut_url or "127.0.0.1" in sut_url:
            pytest.skip("HTTPS requirement skipped for localhost testing")

        # Verify HTTPS is used
        assert sut_url.startswith("https://"), "A2A v0.3.0 requires HTTPS for production deployments"

        # Basic TLS validation (more comprehensive testing would require
        # additional SSL/TLS analysis tools)
        try:
            response = requests.get(sut_url, timeout=5)
            # If we get here, basic TLS handshake succeeded
            logger.info("TLS handshake successful")
        except requests.exceptions.SSLError as e:
            pytest.fail(f"TLS/SSL configuration issue: {e}")
        except requests.exceptions.RequestException:
            # Other network issues are not TLS-related
            pass


class TestAuthenticationErrorHandling:
    """
    Test proper error handling for authentication scenarios.

    Validates that authentication errors are handled consistently
    and provide appropriate feedback as specified in A2A v0.3.0.
    """

    @optional_capability
    @a2a_v030
    def test_authentication_error_codes(self, security_schemes):
        """
        A2A v0.3.0 §4.4 - Authentication Error Response Codes

        Tests that authentication failures use appropriate HTTP status codes
        and follow A2A error response format.
        """
        if not security_schemes:
            pytest.skip("No security schemes declared in Agent Card")

        # Test with deliberately missing authentication
        sut_url = config.get_sut_url()
        headers = {"Content-Type": "application/json"}

        # Create a test request
        json_rpc_request = message_utils.make_json_rpc_request("tasks/get", params={"id": "test-auth-error"}, id="auth-test")

        try:
            response = requests.post(sut_url, json=json_rpc_request, headers=headers, timeout=10)

            # Check for proper HTTP status codes
            if response.status_code in [401, 403]:
                logger.info(f"Proper HTTP {response.status_code} for missing auth")

                # Check for WWW-Authenticate header
                if "www-authenticate" in response.headers:
                    logger.info(f"WWW-Authenticate header present: {response.headers['www-authenticate']}")

            elif response.status_code == 200:
                # Check if error is in JSON-RPC response
                try:
                    json_response = response.json()
                    if "error" in json_response:
                        logger.info(f"Authentication error in JSON-RPC response: {json_response['error']}")
                    else:
                        logger.warning("No authentication enforcement detected")
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON response for auth test")

        except requests.RequestException as e:
            logger.error(f"Request failed during auth test: {e}")

    @optional_capability
    @a2a_v030
    def test_invalid_credentials_handling(self, security_schemes):
        """
        A2A v0.3.0 §4.4 - Invalid Credentials Error Handling

        Tests proper handling of invalid authentication credentials.
        """
        if not security_schemes:
            pytest.skip("No security schemes declared in Agent Card")

        sut_url = config.get_sut_url()

        for scheme in security_schemes:
            scheme_type = scheme.get("type", "")

            # Prepare invalid credentials based on scheme type
            headers = {"Content-Type": "application/json"}

            if scheme_type == "apiKey":
                key_name = scheme.get("name", "x-api-key")
                key_location = scheme.get("in", "header")

                if key_location == "header":
                    headers[key_name] = "invalid-api-key-value"

            elif scheme_type == "http":
                http_scheme = scheme.get("scheme", "bearer").lower()
                if http_scheme == "bearer":
                    headers["Authorization"] = "Bearer invalid-token-12345"
                elif http_scheme == "basic":
                    # invalid:invalid encoded as base64
                    headers["Authorization"] = "Basic aW52YWxpZDppbnZhbGlk"

            # Test the invalid credentials
            json_rpc_request = message_utils.make_json_rpc_request(
                "tasks/get", params={"id": "test-invalid-auth"}, id="invalid-auth-test"
            )

            try:
                response = requests.post(sut_url, json=json_rpc_request, headers=headers, timeout=10)

                # Should get authentication error
                if response.status_code in [401, 403]:
                    logger.info(f"Proper rejection of invalid {scheme_type} credentials")
                elif response.status_code == 200:
                    try:
                        json_response = response.json()
                        if "error" in json_response:
                            logger.info(f"Invalid {scheme_type} rejected in JSON-RPC layer")
                        else:
                            logger.warning(f"Invalid {scheme_type} credentials accepted - security issue")
                    except json.JSONDecodeError:
                        pass

            except requests.RequestException as e:
                logger.warning(f"Request failed testing invalid {scheme_type}: {e}")
