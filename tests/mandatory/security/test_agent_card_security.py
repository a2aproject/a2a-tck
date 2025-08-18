"""
A2A v0.3.0 Protocol: Mandatory Agent Card Security Tests

SPECIFICATION REQUIREMENTS (Section 9.1, 9.2):
- Agent Cards with sensitive information MUST enforce access controls
- Extended Agent Cards MUST require authentication when declared
- Authentication schemes MUST be properly validated
- Unauthorized access to sensitive Agent Cards MUST be prevented

These tests verify that Agent Cards properly implement security controls
for sensitive information and authenticated access as required by A2A v0.3.0.

Reference: A2A v0.3.0 Specification Section 9 (Security Requirements)
"""

import logging
import urllib.parse
from typing import Dict, Any, List, Optional

import pytest
import requests

from tck import agent_card_utils, config
from tests.markers import mandatory
from tests.utils import transport_helpers

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def agent_card_security_info(agent_card_data):
    """
    Extract security-related information from Agent Card for testing.

    Returns dictionary with security configuration details including
    authentication schemes, extended card support, and sensitive fields.
    """
    if agent_card_data is None:
        pytest.skip("Agent Card not available - cannot test security requirements")

    security_info = {
        "has_extended_card": agent_card_data.get("supportsAuthenticatedExtendedCard", False),
        "authentication_schemes": agent_card_utils.get_authentication_schemes(agent_card_data),
        "base_url": agent_card_data.get("url"),
        "security_schemes": agent_card_data.get("securitySchemes", {}),
        "security_requirements": agent_card_data.get("security", []),
        "sensitive_fields": [],
        "public_fields": ["name", "description", "url", "version", "capabilities", "defaultInputModes", "defaultOutputModes"],
    }

    # Identify potentially sensitive fields in the Agent Card
    sensitive_indicators = ["key", "token", "secret", "private", "internal", "admin", "auth"]
    for field_name, field_value in agent_card_data.items():
        if any(indicator in field_name.lower() for indicator in sensitive_indicators):
            security_info["sensitive_fields"].append(field_name)
        elif field_name not in security_info["public_fields"]:
            # Non-standard fields might contain sensitive information
            if isinstance(field_value, (dict, list)) and field_value:
                security_info["sensitive_fields"].append(field_name)

    return security_info


def get_extended_card_url(base_url: str) -> str:
    """
    Construct the extended Agent Card URL according to A2A v0.3.0 specification.

    Per Section 9.1: The endpoint URL is {AgentCard.url}/../agent/authenticatedExtendedCard
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
def test_public_agent_card_access_control(agent_card_data, agent_card_security_info):
    """
    MANDATORY: A2A v0.3.0 Section 9.1 - Public Agent Card Access Controls

    Tests that the public Agent Card is accessible without authentication
    but does not expose sensitive information that should be protected.

    Public Agent Cards MUST be accessible to enable service discovery
    but SHOULD NOT contain sensitive operational details.

    Test Procedure:
    1. Verify public Agent Card is accessible without authentication
    2. Check that sensitive fields are not exposed in public card
    3. Validate that public fields contain appropriate information

    Asserts:
        - Public Agent Card is accessible without authentication
        - No sensitive information is exposed in public card
        - Required public fields are present and valid
    """
    base_url = agent_card_security_info["base_url"]
    if not base_url:
        pytest.fail("Agent Card missing required 'url' field for security testing")

    logger.info(f"Testing public Agent Card access controls: {base_url}")

    try:
        # Test unauthenticated access to public Agent Card
        response = requests.get(base_url, timeout=10)

        # Public Agent Card MUST be accessible without authentication
        assert response.status_code == 200, (
            f"Public Agent Card must be accessible without authentication. Got HTTP {response.status_code}"
        )

        # Verify response is valid JSON Agent Card
        try:
            public_card = response.json()
        except ValueError:
            pytest.fail("Public Agent Card must return valid JSON")

        # Validate required public fields are present
        required_public_fields = ["name", "description", "url", "version", "capabilities"]
        for field in required_public_fields:
            assert field in public_card, f"Public Agent Card missing required field: {field}"

        # Check that sensitive fields are not exposed
        if agent_card_security_info["sensitive_fields"]:
            logger.info(f"Checking {len(agent_card_security_info['sensitive_fields'])} potentially sensitive fields")

            for sensitive_field in agent_card_security_info["sensitive_fields"]:
                if sensitive_field in public_card:
                    # Check if the field contains potentially sensitive data
                    field_value = public_card[sensitive_field]
                    if isinstance(field_value, str) and any(
                        indicator in field_value.lower() for indicator in ["secret", "private", "key", "token", "password"]
                    ):
                        pytest.fail(f"Public Agent Card exposes potentially sensitive field '{sensitive_field}': {field_value}")
                    logger.warning(f"Public card contains field '{sensitive_field}' - verify it's not sensitive")

        logger.info("✅ Public Agent Card access controls properly implemented")

    except requests.exceptions.RequestException as e:
        pytest.fail(f"Failed to access public Agent Card: {e}")


@mandatory
def test_extended_card_access_controls(agent_card_security_info):
    """
    MANDATORY: A2A v0.3.0 Section 9.1 - Extended Agent Card Access Controls

    Tests that extended Agent Cards properly enforce authentication
    when supportsAuthenticatedExtendedCard is declared.

    Extended Agent Cards MUST require authentication and MUST NOT
    be accessible without proper credentials.

    Test Procedure:
    1. Check if extended card is declared in public card
    2. Verify extended card endpoint requires authentication
    3. Test that unauthenticated access is properly rejected

    Asserts:
        - Extended card endpoint exists when declared
        - Authentication is required for extended card access
        - Proper error responses for unauthenticated requests
    """
    if not agent_card_security_info["has_extended_card"]:
        pytest.skip("supportsAuthenticatedExtendedCard not declared - extended card security test not applicable")

    base_url = agent_card_security_info["base_url"]
    extended_url = get_extended_card_url(base_url)

    logger.info(f"Testing extended Agent Card access controls: {extended_url}")
    logger.info(f"Authentication schemes required: {len(agent_card_security_info['authentication_schemes'])}")

    try:
        # Test unauthenticated access to extended Agent Card
        response = requests.get(extended_url, timeout=10)

        # Extended Agent Card MUST require authentication
        if response.status_code == 200:
            # Check if this is actually an extended card or just returns public data
            try:
                card_data = response.json()
                # If it returns the same as public card, it might not be properly secured
                if len(str(card_data)) <= 1000:  # Arbitrary size check - extended should be larger
                    logger.warning("Extended card accessible without auth and appears to be same size as public card")

                pytest.fail(
                    "SECURITY VIOLATION: Extended Agent Card accessible without authentication. "
                    "A2A v0.3.0 Section 9.1 requires authentication for extended cards."
                )
            except ValueError:
                pytest.fail("Extended Agent Card returned invalid JSON without authentication")

        elif response.status_code == 404:
            pytest.fail(
                "SPECIFICATION VIOLATION: Extended Agent Card endpoint not found. "
                "When supportsAuthenticatedExtendedCard=true, endpoint MUST exist."
            )

        elif response.status_code in (401, 403):
            logger.info(f"✅ Extended card properly requires authentication (HTTP {response.status_code})")

            # Verify proper authentication challenge headers
            auth_header = response.headers.get("WWW-Authenticate")
            if auth_header:
                logger.info(f"✅ Proper authentication challenge provided: {auth_header}")
            else:
                logger.warning("Missing WWW-Authenticate header for authentication challenge")

        else:
            logger.warning(f"Unexpected HTTP status for extended card: {response.status_code}")
            pytest.fail(f"Extended card returned unexpected status: {response.status_code}")

    except requests.exceptions.RequestException as e:
        pytest.fail(f"Failed to test extended Agent Card security: {e}")


@mandatory
def test_authentication_scheme_validation(agent_card_security_info):
    """
    MANDATORY: A2A v0.3.0 Section 9.2 - Authentication Scheme Validation

    Tests that declared authentication schemes are properly validated
    and invalid credentials are consistently rejected.

    When authentication schemes are declared, they MUST be properly
    implemented with appropriate validation of credentials.

    Test Procedure:
    1. Test invalid credentials for each declared scheme type
    2. Verify consistent rejection of invalid authentication
    3. Check proper error handling for malformed credentials

    Asserts:
        - Invalid credentials are consistently rejected
        - Proper HTTP status codes for authentication failures
        - Consistent security enforcement across scheme types
    """
    auth_schemes = agent_card_security_info["authentication_schemes"]
    if not auth_schemes:
        pytest.skip("No authentication schemes declared - cannot test scheme validation")

    if not agent_card_security_info["has_extended_card"]:
        pytest.skip("No extended card declared - cannot test authentication scheme validation")

    base_url = agent_card_security_info["base_url"]
    extended_url = get_extended_card_url(base_url)

    logger.info(f"Testing authentication scheme validation: {extended_url}")
    logger.info(f"Testing {len(auth_schemes)} authentication schemes")

    validation_results = []

    for i, scheme in enumerate(auth_schemes):
        scheme_type = scheme.get("type", "unknown").lower()
        scheme_name = scheme.get("scheme", "unknown")

        logger.info(f"Testing invalid credentials for scheme {i + 1}: {scheme_type}")

        # Test multiple invalid credential scenarios for each scheme
        test_scenarios = [
            ("empty", {}),
            ("malformed", {"Authorization": "Malformed auth header"}),
            ("invalid_type", {"Authorization": f"InvalidType invalid-token-{i}"}),
        ]

        # Add scheme-specific invalid credentials
        if scheme_type == "http" and scheme_name.lower() == "bearer":
            test_scenarios.extend(
                [
                    ("invalid_bearer", {"Authorization": "Bearer invalid-bearer-token-12345"}),
                    ("expired_bearer", {"Authorization": "Bearer expired.token.signature"}),
                ]
            )
        elif scheme_type == "http" and scheme_name.lower() == "basic":
            test_scenarios.extend(
                [
                    ("invalid_basic", {"Authorization": "Basic aW52YWxpZDppbnZhbGlk"}),  # invalid:invalid
                    ("malformed_basic", {"Authorization": "Basic not-base64-encoded"}),
                ]
            )
        elif scheme_type == "apikey":
            key_name = scheme.get("name", "X-API-Key")
            key_location = scheme.get("in", "header")

            if key_location == "header":
                test_scenarios.extend(
                    [
                        ("invalid_apikey", {key_name: "invalid-api-key-12345"}),
                        ("empty_apikey", {key_name: ""}),
                    ]
                )
        elif scheme_type == "oauth2":
            test_scenarios.extend(
                [
                    ("invalid_oauth2", {"Authorization": "Bearer invalid-oauth2-token"}),
                    ("malformed_oauth2", {"Authorization": "Bearer malformed.oauth2.token"}),
                ]
            )

        scheme_validation_passed = True

        for scenario_name, headers in test_scenarios:
            try:
                response = requests.get(extended_url, headers=headers, timeout=10)

                # Invalid credentials MUST be rejected
                if response.status_code not in (401, 403):
                    if response.status_code == 200:
                        logger.error(f"SECURITY FAILURE: {scheme_type} scheme accepted invalid credentials ({scenario_name})")
                        scheme_validation_passed = False
                    else:
                        logger.warning(
                            f"Unexpected status for invalid {scheme_type} credentials ({scenario_name}): {response.status_code}"
                        )
                else:
                    logger.debug(
                        f"✅ Invalid {scheme_type} credentials properly rejected ({scenario_name}): HTTP {response.status_code}"
                    )

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed for {scheme_type} scheme ({scenario_name}): {e}")

        validation_results.append(
            {"scheme_type": scheme_type, "scheme_name": scheme_name, "validation_passed": scheme_validation_passed}
        )

    # Verify all schemes properly validate credentials
    failed_schemes = [r for r in validation_results if not r["validation_passed"]]
    if failed_schemes:
        failed_names = [f"{r['scheme_type']}({r['scheme_name']})" for r in failed_schemes]
        pytest.fail(f"Authentication schemes failed validation: {', '.join(failed_names)}")

    logger.info("✅ All declared authentication schemes properly validate credentials")


@mandatory
def test_sensitive_information_protection(agent_card_data, agent_card_security_info):
    """
    MANDATORY: A2A v0.3.0 Section 9.1 - Sensitive Information Protection

    Tests that sensitive information is not exposed in public Agent Cards
    and is properly protected through authentication requirements.

    Agent Cards MUST NOT expose sensitive operational details, credentials,
    or internal configuration in publicly accessible endpoints.

    Test Procedure:
    1. Scan public Agent Card for potentially sensitive patterns
    2. Verify no credentials or secrets are exposed
    3. Check that internal URLs/endpoints are not leaked

    Asserts:
        - No credentials or API keys in public Agent Card
        - No internal URLs or sensitive endpoints exposed
        - Sensitive configuration is properly protected
    """
    logger.info("Testing sensitive information protection in Agent Card")

    # Define patterns that indicate sensitive information
    sensitive_patterns = [
        # Credential patterns
        r"(?i)(api[_-]?key|secret|token|password|credential)",
        r"(?i)(private[_-]?key|secret[_-]?key)",
        r"(?i)(access[_-]?token|bearer[_-]?token)",
        r"(?i)(client[_-]?secret|app[_-]?secret)",
        # URL patterns that might be internal
        r"(?i)(localhost|127\.0\.0\.1|192\.168\.|10\.|172\.1[6-9]\.|172\.2[0-9]\.|172\.3[01]\.)",
        r"(?i)(internal|private|admin|debug|test).*(?:url|endpoint|host)",
        # Configuration that might be sensitive
        r"(?i)(database|db)[_-]?(url|host|connection)",
        r"(?i)(redis|mongo|sql)[_-]?(url|host|connection)",
    ]

    import re

    # Convert Agent Card to string for pattern matching
    card_str = str(agent_card_data).lower()

    violations = []

    for pattern in sensitive_patterns:
        matches = re.findall(pattern, card_str)
        if matches:
            violations.extend(matches)

    # Check specific fields that commonly contain sensitive data
    sensitive_field_checks = {
        "adminUrl": "Admin URLs should not be in public Agent Card",
        "internalUrl": "Internal URLs should not be in public Agent Card",
        "debugEndpoint": "Debug endpoints should not be in public Agent Card",
        "privateConfig": "Private configuration should not be in public Agent Card",
        "secrets": "Secrets should not be in public Agent Card",
        "credentials": "Credentials should not be in public Agent Card",
    }

    for field_name, violation_msg in sensitive_field_checks.items():
        if field_name in agent_card_data:
            violations.append(f"{field_name}: {violation_msg}")

    # Special check for URLs that might expose internal information
    url_fields = ["url", "endpoint"]
    for url_field in url_fields:
        if url_field in agent_card_data:
            url_value = agent_card_data[url_field]
            if isinstance(url_value, str):
                # Check for development/internal URLs
                if any(internal in url_value.lower() for internal in ["localhost", "127.0.0.1", "192.168.", "10."]):
                    violations.append(f"{url_field}: Contains internal/development URL: {url_value}")

                # Check for non-standard ports that might indicate development
                parsed = urllib.parse.urlparse(url_value)
                if parsed.port and parsed.port not in [80, 443, 8080]:
                    logger.warning(f"Agent Card {url_field} uses non-standard port {parsed.port}: {url_value}")

    if violations:
        logger.error("Sensitive information detected in public Agent Card:")
        for violation in violations:
            logger.error(f"  - {violation}")

        pytest.fail(
            f"SECURITY VIOLATION: Public Agent Card exposes sensitive information. "
            f"Found {len(violations)} potential issues. "
            f"A2A v0.3.0 Section 9.1 requires protection of sensitive data."
        )

    logger.info("✅ No sensitive information detected in public Agent Card")


@mandatory
def test_security_scheme_consistency(agent_card_security_info):
    """
    MANDATORY: A2A v0.3.0 Section 9.2 - Security Scheme Consistency

    Tests that declared security schemes are consistent and properly configured
    according to OpenAPI 3.x Security Scheme specifications.

    Security schemes MUST be properly defined with all required fields
    and MUST follow standard security scheme formats.

    Test Procedure:
    1. Validate security scheme definitions
    2. Check required fields for each scheme type
    3. Verify scheme configurations are consistent

    Asserts:
        - All security schemes have required fields
        - Scheme types are valid OpenAPI 3.x types
        - Security scheme configurations are consistent
    """
    security_schemes = agent_card_security_info["security_schemes"]
    auth_schemes = agent_card_security_info["authentication_schemes"]

    if not security_schemes and not auth_schemes:
        pytest.skip("No security schemes declared - cannot test scheme consistency")

    logger.info(f"Testing security scheme consistency")
    logger.info(f"Security schemes defined: {len(security_schemes)}")
    logger.info(f"Authentication schemes available: {len(auth_schemes)}")

    # Valid OpenAPI 3.x security scheme types
    valid_scheme_types = ["apiKey", "http", "oauth2", "openIdConnect", "mutualTLS"]

    consistency_issues = []

    # Validate security scheme definitions
    for scheme_name, scheme_def in security_schemes.items():
        if not isinstance(scheme_def, dict):
            consistency_issues.append(f"Security scheme '{scheme_name}' is not an object")
            continue

        # Check required 'type' field
        scheme_type = scheme_def.get("type")
        if not scheme_type:
            consistency_issues.append(f"Security scheme '{scheme_name}' missing required 'type' field")
            continue

        if scheme_type not in valid_scheme_types:
            consistency_issues.append(f"Security scheme '{scheme_name}' has invalid type '{scheme_type}'")

        # Validate type-specific required fields
        if scheme_type == "apiKey":
            if "name" not in scheme_def:
                consistency_issues.append(f"API Key scheme '{scheme_name}' missing required 'name' field")
            if "in" not in scheme_def:
                consistency_issues.append(f"API Key scheme '{scheme_name}' missing required 'in' field")
            elif scheme_def["in"] not in ["query", "header", "cookie"]:
                consistency_issues.append(f"API Key scheme '{scheme_name}' has invalid 'in' value: {scheme_def['in']}")

        elif scheme_type == "http":
            if "scheme" not in scheme_def:
                consistency_issues.append(f"HTTP scheme '{scheme_name}' missing required 'scheme' field")
            elif scheme_def["scheme"].lower() not in ["basic", "bearer", "digest"]:
                logger.warning(f"HTTP scheme '{scheme_name}' uses non-standard scheme: {scheme_def['scheme']}")

        elif scheme_type == "oauth2":
            if "flows" not in scheme_def:
                consistency_issues.append(f"OAuth2 scheme '{scheme_name}' missing required 'flows' field")

        elif scheme_type == "openIdConnect":
            if "openIdConnectUrl" not in scheme_def:
                consistency_issues.append(f"OpenID Connect scheme '{scheme_name}' missing required 'openIdConnectUrl' field")

    # Check consistency between securitySchemes and available authentication schemes
    if auth_schemes:
        scheme_names_in_auth = {scheme.get("name", f"scheme_{i}") for i, scheme in enumerate(auth_schemes)}
        scheme_names_in_security = set(security_schemes.keys())

        # It's okay if they don't match exactly (legacy support), but log any differences
        if scheme_names_in_security and scheme_names_in_auth:
            missing_in_security = scheme_names_in_auth - scheme_names_in_security
            missing_in_auth = scheme_names_in_security - scheme_names_in_auth

            if missing_in_security:
                logger.warning(f"Authentication schemes not in securitySchemes: {missing_in_security}")
            if missing_in_auth:
                logger.warning(f"Security schemes not in authentication: {missing_in_auth}")

    if consistency_issues:
        logger.error("Security scheme consistency issues found:")
        for issue in consistency_issues:
            logger.error(f"  - {issue}")

        pytest.fail(
            f"SPECIFICATION VIOLATION: Security scheme definitions are inconsistent. "
            f"Found {len(consistency_issues)} issues. "
            f"A2A v0.3.0 Section 9.2 requires proper security scheme definitions."
        )

    logger.info("✅ Security scheme definitions are consistent and properly configured")
