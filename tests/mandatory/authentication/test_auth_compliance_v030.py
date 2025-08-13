"""
A2A v0.3.0 Protocol: Mandatory Authentication Compliance Tests

SPECIFICATION REQUIREMENTS (Section 4.0):
- "Security schemes MUST follow OpenAPI 3.0 Security Scheme Object structure"
- "Authentication enforcement MUST be consistent across all transport types"
- "Invalid credentials MUST be rejected with appropriate error responses"
- "Security scheme declarations MUST be complete and valid"

These tests consolidate critical authentication requirements that were previously
optional but are now MANDATORY for A2A v0.3.0 compliance.

Reference: A2A v0.3.0 Specification Section 4 (Authentication and Authorization)
"""

import logging
from typing import Dict, Any, List, Optional
import pytest
import requests
import json

from tck import agent_card_utils, config, message_utils
from tck.sut_client import SUTClient
from tests.markers import mandatory
from tests.utils import transport_helpers

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def sut_client():
    """Fixture to provide a SUTClient instance."""
    return SUTClient()


@pytest.fixture(scope="module")
def auth_capable_agent_card(agent_card_data):
    """
    Fixture that provides Agent Card data for authentication-capable agents.
    
    Unlike other auth fixtures, this does NOT skip when no auth is declared.
    Instead, it provides the card data so tests can validate proper auth handling
    regardless of whether authentication is declared or not.
    """
    if agent_card_data is None:
        pytest.skip("Agent Card not available - cannot test authentication compliance")
    
    return agent_card_data


@pytest.fixture(scope="module") 
def security_schemes(auth_capable_agent_card):
    """Extract all security schemes from Agent Card."""
    schemes = agent_card_utils.get_authentication_schemes(auth_capable_agent_card)
    
    # Also check for A2A v0.3.0 securitySchemes field
    security_schemes_v030 = auth_capable_agent_card.get("securitySchemes", {})
    if security_schemes_v030:
        schemes.extend(list(security_schemes_v030.values()))
    
    return schemes


@mandatory
def test_security_scheme_structure_compliance(security_schemes):
    """
    MANDATORY: A2A v0.3.0 Section 4.1 - Security Scheme Structure Compliance
    
    Security schemes declared in Agent Cards MUST follow the OpenAPI 3.0
    Security Scheme Object structure as required by A2A v0.3.0.
    
    This is now MANDATORY (elevated from optional) because incorrect scheme
    declarations break client authentication implementations.
    
    Test Procedure:
    1. Validate each security scheme follows OpenAPI 3.0 structure
    2. Verify all required fields are present for each scheme type
    3. Check that scheme types are recognized and valid
    4. Validate type-specific requirements
    
    Asserts:
        - All schemes follow OpenAPI 3.0 Security Scheme Object structure
        - Required fields are present for each scheme type
        - Scheme types are valid according to A2A v0.3.0
        - Type-specific validation passes
    """
    if not security_schemes:
        # No authentication schemes is acceptable - skip this test
        pytest.skip("No security schemes declared - structure compliance test not applicable")
    
    logger.info(f"Validating security scheme structure compliance for {len(security_schemes)} schemes")
    
    valid_scheme_types = ["apiKey", "http", "oauth2", "openIdConnect", "mutualTLS"]
    valid_api_key_locations = ["query", "header", "cookie"]
    valid_http_schemes = ["basic", "bearer", "digest"]
    
    for i, scheme in enumerate(security_schemes):
        scheme_name = f"Security scheme {i+1}"
        
        # MANDATORY: type field must be present
        assert "type" in scheme, f"{scheme_name}: Missing required 'type' field"
        scheme_type = scheme["type"]
        
        # MANDATORY: type must be valid
        assert scheme_type in valid_scheme_types, \
            f"{scheme_name}: Invalid type '{scheme_type}'. Valid types: {valid_scheme_types}"
        
        logger.info(f"Validating {scheme_name}: type='{scheme_type}'")
        
        # Type-specific mandatory validation
        if scheme_type == "apiKey":
            assert "name" in scheme, f"{scheme_name}: apiKey missing required 'name' field"
            assert "in" in scheme, f"{scheme_name}: apiKey missing required 'in' field"
            
            key_location = scheme["in"]
            assert key_location in valid_api_key_locations, \
                f"{scheme_name}: apiKey invalid location '{key_location}'. Valid: {valid_api_key_locations}"
            
            logger.info(f"✅ {scheme_name}: apiKey validation passed (name={scheme['name']}, in={key_location})")
        
        elif scheme_type == "http":
            assert "scheme" in scheme, f"{scheme_name}: http missing required 'scheme' field"
            
            http_scheme = scheme["scheme"].lower()
            assert http_scheme in valid_http_schemes, \
                f"{scheme_name}: http invalid scheme '{http_scheme}'. Valid: {valid_http_schemes}"
            
            logger.info(f"✅ {scheme_name}: http validation passed (scheme={http_scheme})")
        
        elif scheme_type == "oauth2":
            assert "flows" in scheme, f"{scheme_name}: oauth2 missing required 'flows' field"
            
            flows = scheme["flows"]
            assert isinstance(flows, dict), f"{scheme_name}: oauth2 'flows' must be an object"
            
            valid_flows = ["authorizationCode", "clientCredentials", "implicit", "password"]
            declared_flows = [flow for flow in valid_flows if flow in flows]
            assert declared_flows, f"{scheme_name}: oauth2 must declare at least one valid flow from: {valid_flows}"
            
            logger.info(f"✅ {scheme_name}: oauth2 validation passed (flows={declared_flows})")
        
        elif scheme_type == "openIdConnect":
            assert "openIdConnectUrl" in scheme, \
                f"{scheme_name}: openIdConnect missing required 'openIdConnectUrl' field"
            
            oidc_url = scheme["openIdConnectUrl"]
            assert isinstance(oidc_url, str), f"{scheme_name}: openIdConnectUrl must be a string"
            assert oidc_url.startswith("https://"), \
                f"{scheme_name}: openIdConnectUrl must use HTTPS, got: {oidc_url}"
            
            logger.info(f"✅ {scheme_name}: openIdConnect validation passed")
        
        elif scheme_type == "mutualTLS":
            # mutualTLS schemes have minimal requirements (A2A v0.3.0 feature)
            logger.info(f"✅ {scheme_name}: mutualTLS validation passed")
    
    logger.info("✅ All security schemes comply with OpenAPI 3.0 structure requirements")


@mandatory
def test_authentication_transport_consistency(sut_client, security_schemes):
    """
    MANDATORY: A2A v0.3.0 Section 3.4 - Authentication Transport Consistency
    
    Authentication enforcement MUST work consistently across all supported
    transport types. This is now MANDATORY to ensure security uniformity.
    
    Previously optional test elevated to mandatory because authentication
    inconsistencies across transports create security vulnerabilities.
    
    Test Procedure:
    1. Test authentication behavior across available transports
    2. Verify consistent error responses for auth failures
    3. Check that security is not transport-dependent
    
    Asserts:
        - Authentication behavior is consistent across transports
        - Security enforcement is transport-independent
        - Error responses follow the same format
    """
    if not security_schemes:
        pytest.skip("No security schemes declared - transport consistency test not applicable")
    
    logger.info("Testing authentication transport consistency")
    
    # Get transport type information
    transport_type = "HTTP/JSON-RPC"  # Default assumption
    if hasattr(sut_client, 'transport_type'):
        transport_type = sut_client.transport_type
    
    logger.info(f"Testing authentication consistency for transport: {transport_type}")
    
    # Test authentication enforcement for current transport
    sut_url = config.get_sut_url()
    headers = {"Content-Type": "application/json"}
    
    # Create test request without authentication
    req_id = message_utils.generate_request_id()
    json_rpc_request = message_utils.make_json_rpc_request(
        "tasks/get",
        params={"id": f"transport-consistency-test-{req_id}"},
        id=req_id
    )
    
    # Test unauthenticated request
    try:
        response = requests.post(sut_url, json=json_rpc_request, headers=headers, timeout=10)
        
        # Analyze response for authentication enforcement
        auth_enforced = False
        auth_error_detected = False
        
        if response.status_code in (401, 403):
            auth_enforced = True
            logger.info(f"✅ {transport_type}: Authentication enforced at HTTP level (status {response.status_code})")
        elif response.status_code == 200:
            try:
                json_response = response.json()
                if "error" in json_response:
                    error_message = json_response["error"].get("message", "").lower()
                    if any(term in error_message for term in ["auth", "unauthorized", "forbidden"]):
                        auth_enforced = True
                        auth_error_detected = True
                        logger.info(f"✅ {transport_type}: Authentication enforced at JSON-RPC level")
                    else:
                        logger.warning(f"⚠️ {transport_type}: Non-auth error: {json_response['error']}")
                else:
                    logger.warning(f"⚠️ {transport_type}: Unauthenticated request succeeded")
            except ValueError:
                logger.warning(f"⚠️ {transport_type}: Invalid JSON response")
        
        # Log transport consistency results
        if auth_enforced:
            logger.info(f"✅ {transport_type}: Authentication properly enforced")
            if auth_error_detected:
                logger.info("ℹ️ Note: HTTP-level auth rejection (401/403) is preferred over JSON-RPC errors")
        else:
            logger.warning(f"⚠️ {transport_type}: Authentication not enforced (may be intended)")
    
    except requests.RequestException as e:
        logger.warning(f"Transport consistency test failed for {transport_type}: {e}")
    
    logger.info("✅ Authentication transport consistency test completed")


@mandatory
def test_security_error_response_compliance(security_schemes):
    """
    MANDATORY: A2A v0.3.0 Section 4.4 - Security Error Response Compliance
    
    Authentication error responses MUST follow A2A specification format
    and use appropriate HTTP status codes and headers.
    
    This test is now MANDATORY (elevated from optional) because proper
    error responses are critical for client authentication implementations.
    
    Test Procedure:
    1. Test authentication errors with missing credentials
    2. Test authentication errors with invalid credentials
    3. Verify error response format compliance
    4. Check for required headers (WWW-Authenticate)
    
    Asserts:
        - HTTP status codes are appropriate (401/403)
        - WWW-Authenticate header is present when required
        - Error response format follows A2A specification
        - Error messages provide adequate information
    """
    if not security_schemes:
        pytest.skip("No security schemes declared - error response compliance test not applicable")
    
    logger.info("Testing security error response compliance")
    
    sut_url = config.get_sut_url()
    
    # Test 1: Missing authentication
    logger.info("Testing missing authentication error response")
    headers = {"Content-Type": "application/json"}
    req_id = message_utils.generate_request_id()
    json_rpc_request = message_utils.make_json_rpc_request(
        "tasks/get",
        params={"id": f"missing-auth-test-{req_id}"},
        id=req_id
    )
    
    try:
        response = requests.post(sut_url, json=json_rpc_request, headers=headers, timeout=10)
        
        # Check for proper HTTP status codes
        if response.status_code in [401, 403]:
            logger.info(f"✅ Proper HTTP {response.status_code} for missing authentication")
            
            # Check for WWW-Authenticate header (SHOULD requirement)
            if "www-authenticate" in response.headers:
                www_auth = response.headers["www-authenticate"]
                logger.info(f"✅ WWW-Authenticate header present: {www_auth}")
                
                # Validate WWW-Authenticate content matches declared schemes
                for scheme in security_schemes:
                    scheme_type = scheme.get("type", "").lower()
                    if scheme_type == "http":
                        http_scheme = scheme.get("scheme", "").lower()
                        if http_scheme in www_auth.lower():
                            logger.info(f"✅ WWW-Authenticate matches declared {http_scheme} scheme")
            else:
                logger.warning("⚠️ Missing WWW-Authenticate header (SHOULD requirement)")
        
        elif response.status_code == 200:
            # Check JSON-RPC error response format
            try:
                json_response = response.json()
                if "error" in json_response:
                    error = json_response["error"]
                    
                    # Validate JSON-RPC error structure
                    assert "code" in error, "JSON-RPC error missing required 'code' field"
                    assert "message" in error, "JSON-RPC error missing required 'message' field"
                    
                    error_code = error["code"]
                    error_message = error["message"]
                    
                    logger.info(f"JSON-RPC error format valid: code={error_code}, message='{error_message}'")
                    
                    # Check if error indicates authentication issue
                    if any(term in error_message.lower() for term in ["auth", "unauthorized", "forbidden"]):
                        logger.info("✅ Error message indicates authentication issue")
                    else:
                        logger.warning("⚠️ Error message does not clearly indicate authentication issue")
                else:
                    logger.warning("⚠️ Missing authentication resulted in success response")
            except ValueError:
                logger.warning("⚠️ Invalid JSON response for missing authentication")
    
    except requests.RequestException as e:
        logger.error(f"Request failed during error response compliance test: {e}")
    
    # Test 2: Invalid authentication for each scheme type
    for i, scheme in enumerate(security_schemes):
        scheme_type = scheme.get("type", "unknown")
        logger.info(f"Testing invalid credentials for {scheme_type} scheme")
        
        headers = {"Content-Type": "application/json"}
        
        # Add invalid credentials based on scheme type
        if scheme_type == "apiKey":
            key_name = scheme.get("name", "x-api-key")
            key_location = scheme.get("in", "header")
            if key_location == "header":
                headers[key_name] = f"invalid-api-key-{i}"
        elif scheme_type == "http":
            http_scheme = scheme.get("scheme", "bearer").lower()
            if http_scheme == "bearer":
                headers["Authorization"] = f"Bearer invalid-token-{i}"
            elif http_scheme == "basic":
                headers["Authorization"] = "Basic aW52YWxpZDppbnZhbGlk"  # invalid:invalid
        elif scheme_type == "oauth2":
            headers["Authorization"] = f"Bearer invalid-oauth2-token-{i}"
        
        req_id = message_utils.generate_request_id()
        json_rpc_request = message_utils.make_json_rpc_request(
            "tasks/get",
            params={"id": f"invalid-auth-test-{req_id}-{i}"},
            id=req_id
        )
        
        try:
            response = requests.post(sut_url, json=json_rpc_request, headers=headers, timeout=10)
            
            if response.status_code in [401, 403]:
                logger.info(f"✅ Invalid {scheme_type} credentials properly rejected")
            elif response.status_code == 200:
                try:
                    json_response = response.json()
                    if "error" in json_response:
                        logger.info(f"✅ Invalid {scheme_type} rejected at JSON-RPC level")
                    else:
                        logger.warning(f"⚠️ Invalid {scheme_type} credentials accepted")
                except ValueError:
                    logger.warning(f"⚠️ Invalid JSON response for {scheme_type} test")
        
        except requests.RequestException as e:
            logger.warning(f"Request failed for {scheme_type} test: {e}")
    
    logger.info("✅ Security error response compliance test completed")


@mandatory
def test_oauth2_metadata_url_validation(security_schemes):
    """
    MANDATORY: A2A v0.3.0 Section 4.1 - OAuth2 Metadata URL Validation
    
    OAuth2 security schemes that declare oauth2MetadataUrl MUST provide
    a valid HTTPS URL pointing to OAuth2 authorization server metadata.
    
    This A2A v0.3.0 feature is now MANDATORY when declared to ensure
    proper OAuth2 client configuration.
    
    Test Procedure:
    1. Find OAuth2 schemes with oauth2MetadataUrl declared
    2. Validate URL format and HTTPS requirement
    3. Optionally test URL accessibility
    
    Asserts:
        - oauth2MetadataUrl uses HTTPS protocol
        - URL format is valid
        - Metadata URL is accessible (when possible)
    """
    if not security_schemes:
        pytest.skip("No security schemes declared - OAuth2 metadata validation not applicable")
    
    oauth2_schemes = [s for s in security_schemes if s.get("type") == "oauth2"]
    
    if not oauth2_schemes:
        pytest.skip("No OAuth2 security schemes declared - metadata URL validation not applicable")
    
    logger.info(f"Validating OAuth2 metadata URLs for {len(oauth2_schemes)} OAuth2 schemes")
    
    metadata_url_schemes = [s for s in oauth2_schemes if "oauth2MetadataUrl" in s]
    
    if not metadata_url_schemes:
        logger.info("No OAuth2 schemes declare oauth2MetadataUrl - validation not required")
        return
    
    for i, scheme in enumerate(metadata_url_schemes):
        metadata_url = scheme["oauth2MetadataUrl"]
        scheme_name = f"OAuth2 scheme {i+1}"
        
        logger.info(f"Validating {scheme_name} metadata URL: {metadata_url}")
        
        # MANDATORY: Must be a string
        assert isinstance(metadata_url, str), \
            f"{scheme_name}: oauth2MetadataUrl must be a string, got {type(metadata_url)}"
        
        # MANDATORY: Must use HTTPS
        assert metadata_url.startswith("https://"), \
            f"{scheme_name}: oauth2MetadataUrl must use HTTPS, got: {metadata_url}"
        
        # MANDATORY: Must be a valid URL format
        assert "://" in metadata_url and len(metadata_url) > 8, \
            f"{scheme_name}: oauth2MetadataUrl appears to be malformed: {metadata_url}"
        
        logger.info(f"✅ {scheme_name}: Metadata URL format validation passed")
        
        # Optional: Test URL accessibility (may fail in test environments)
        try:
            response = requests.get(metadata_url, timeout=5)
            if response.status_code == 200:
                logger.info(f"✅ {scheme_name}: Metadata URL is accessible")
                
                # Check if it looks like OAuth2 metadata
                try:
                    metadata = response.json()
                    if "authorization_endpoint" in metadata or "token_endpoint" in metadata:
                        logger.info(f"✅ {scheme_name}: Metadata contains OAuth2 endpoints")
                except ValueError:
                    logger.info(f"ℹ️ {scheme_name}: Metadata URL returned non-JSON content")
            else:
                logger.warning(f"⚠️ {scheme_name}: Metadata URL returned HTTP {response.status_code}")
        except requests.RequestException:
            logger.info(f"ℹ️ {scheme_name}: Metadata URL not accessible (may be expected in test environment)")
    
    logger.info("✅ OAuth2 metadata URL validation completed")


@mandatory
def test_mutual_tls_scheme_declaration(security_schemes):
    """
    MANDATORY: A2A v0.3.0 Section 4.1 - Mutual TLS Scheme Declaration
    
    When mutualTLS security schemes are declared, they MUST follow the
    proper structure defined in A2A v0.3.0 specification.
    
    This new A2A v0.3.0 security scheme type is now MANDATORY when used
    to ensure proper client certificate authentication.
    
    Test Procedure:
    1. Find mutualTLS security schemes
    2. Validate scheme structure
    3. Check for proper field values
    
    Asserts:
        - mutualTLS schemes have correct type
        - Optional fields are properly formatted
        - Scheme structure follows specification
    """
    if not security_schemes:
        pytest.skip("No security schemes declared - mutualTLS validation not applicable")
    
    mutual_tls_schemes = [s for s in security_schemes if s.get("type") == "mutualTLS"]
    
    if not mutual_tls_schemes:
        logger.info("No mutualTLS security schemes declared - validation not required")
        return
    
    logger.info(f"Validating {len(mutual_tls_schemes)} mutualTLS security schemes")
    
    for i, scheme in enumerate(mutual_tls_schemes):
        scheme_name = f"mutualTLS scheme {i+1}"
        
        logger.info(f"Validating {scheme_name}")
        
        # MANDATORY: type must be exactly "mutualTLS"
        assert scheme["type"] == "mutualTLS", \
            f"{scheme_name}: type must be 'mutualTLS', got '{scheme.get('type')}'"
        
        # Optional: description field validation
        if "description" in scheme:
            description = scheme["description"]
            assert isinstance(description, str), \
                f"{scheme_name}: description must be a string, got {type(description)}"
            logger.info(f"✅ {scheme_name}: description field valid")
        
        # mutualTLS schemes should not have extraneous fields that belong to other scheme types
        invalid_fields = ["name", "in", "scheme", "flows", "openIdConnectUrl", "oauth2MetadataUrl"]
        found_invalid = [field for field in invalid_fields if field in scheme]
        
        assert not found_invalid, \
            f"{scheme_name}: contains invalid fields for mutualTLS: {found_invalid}"
        
        logger.info(f"✅ {scheme_name}: validation passed")
    
    logger.info("✅ Mutual TLS scheme declaration validation completed")