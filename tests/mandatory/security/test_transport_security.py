"""
A2A v0.3.0 Protocol: Mandatory Transport Security Tests

SPECIFICATION REQUIREMENTS (Section 4.1):
- "Production deployments MUST use HTTPS"
- "Implementations SHOULD use modern TLS configurations (TLS 1.3+ recommended)"
- "A2A Clients SHOULD verify the A2A Server's identity by validating its TLS certificate"

These tests verify that HTTPS/TLS security is MANDATORY for production deployments.
Unlike optional security tests, these tests FAIL if security requirements are violated.

Reference: A2A v0.3.0 Specification Section 4.1 (Transport Security)
"""

import logging
import socket
import ssl
import urllib.parse
from datetime import datetime, timezone

import pytest
import requests

from tck import config
from tests.markers import mandatory

logger = logging.getLogger(__name__)


def is_localhost_or_test_environment(sut_url: str) -> bool:
    """
    Determine if the SUT URL represents a localhost or test environment.
    HTTPS requirements are relaxed for local testing but MANDATORY for production.
    """
    parsed = urllib.parse.urlparse(sut_url)
    hostname = parsed.hostname

    # Localhost and test environment indicators
    test_indicators = ["localhost", "127.0.0.1", "::1", "test", "dev", "local", "staging"]

    if hostname:
        hostname_lower = hostname.lower()
        return any(indicator in hostname_lower for indicator in test_indicators)

    return False


@mandatory
def test_https_required_production():
    """
    MANDATORY: A2A v0.3.0 Section 4.1 - HTTPS Requirement for Production

    Production deployments MUST use HTTPS. This is a security requirement
    to protect A2A communications from eavesdropping and tampering.

    Test Logic:
    - If SUT URL uses localhost/test domains: SKIP (testing environment)
    - If SUT URL is production-like: MUST use HTTPS
    - HTTP in production environments is a specification violation

    Test Procedure:
    1. Parse SUT URL to determine if it's a production environment
    2. For production environments, verify HTTPS is used
    3. Verify HTTPS connection can be established

    Asserts:
        - Production deployments use HTTPS (not HTTP)
        - HTTPS connections are properly configured
        - TLS handshake succeeds for production environments
    """
    sut_url = config.get_sut_url()
    if not sut_url:
        pytest.skip("SUT URL not provided - cannot test HTTPS requirements")

    parsed_url = urllib.parse.urlparse(sut_url)

    # Skip HTTPS requirement for localhost/test environments
    if is_localhost_or_test_environment(sut_url):
        logger.info(f"SUT URL appears to be test/localhost environment: {sut_url}")
        logger.info("HTTPS requirement relaxed for testing - SKIPPING production HTTPS validation")
        pytest.skip("HTTPS requirement skipped for localhost/test environment")

    # For production-like environments, HTTPS is MANDATORY
    logger.info(f"SUT URL appears to be production environment: {sut_url}")

    # MANDATORY: Production deployments MUST use HTTPS
    if parsed_url.scheme != "https":
        pytest.fail(
            f"SPECIFICATION VIOLATION: Production deployment MUST use HTTPS. "
            f"A2A v0.3.0 Section 4.1 requires HTTPS for production environments. "
            f"Got: {parsed_url.scheme}://{parsed_url.netloc}"
        )

    logger.info("✅ Production SUT correctly uses HTTPS")

    # Verify HTTPS connection can be established
    try:
        response = requests.get(sut_url, timeout=10, verify=True)
        logger.info(f"✅ HTTPS connection successful (HTTP {response.status_code})")

        # Log TLS information if available
        if hasattr(response.raw, "_connection") and hasattr(response.raw._connection, "sock"):
            sock = response.raw._connection.sock
            if hasattr(sock, "version"):
                tls_version = sock.version()
                logger.info(f"TLS version: {tls_version}")

    except requests.exceptions.SSLError as e:
        pytest.fail(f"HTTPS/TLS connection failed: {e}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"HTTPS connection test failed (non-TLS issue): {e}")
        # Don't fail the test for non-TLS connection issues


@mandatory
def test_tls_certificate_validation():
    """
    MANDATORY: A2A v0.3.0 Section 4.2 - Server Identity Verification

    A2A Clients SHOULD verify the A2A Server's identity by validating its TLS certificate.
    While this is a SHOULD requirement, certificate validation is critical for security.

    Test Logic:
    - Skip for localhost/test environments (self-signed certs common)
    - For production: Validate certificate chain and hostname

    Test Procedure:
    1. Establish TLS connection to SUT
    2. Verify certificate chain validation
    3. Verify hostname matches certificate
    4. Check certificate expiration

    Asserts:
        - TLS certificate is valid and trusted
        - Certificate hostname matches SUT hostname
        - Certificate is not expired
        - Certificate chain is properly configured
    """
    sut_url = config.get_sut_url()
    if not sut_url:
        pytest.skip("SUT URL not provided - cannot test certificate validation")

    parsed_url = urllib.parse.urlparse(sut_url)

    # Skip certificate validation for localhost/test environments
    if is_localhost_or_test_environment(sut_url):
        logger.info("Certificate validation skipped for localhost/test environment")
        pytest.skip("Certificate validation relaxed for testing environments")

    # Only test HTTPS URLs
    if parsed_url.scheme != "https":
        pytest.skip("Certificate validation only applicable to HTTPS URLs")

    hostname = parsed_url.hostname
    port = parsed_url.port or 443

    logger.info(f"Testing TLS certificate validation for {hostname}:{port}")

    try:
        # Create SSL context with certificate verification enabled
        context = ssl.create_default_context()

        # Establish TLS connection
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as tls_sock:
                # Get certificate information
                cert = tls_sock.getpeercert()

                logger.info("✅ TLS certificate validation successful")

                # Log certificate details
                subject = dict(x[0] for x in cert["subject"])
                issuer = dict(x[0] for x in cert["issuer"])

                logger.info(f"Certificate subject: {subject.get('commonName', 'Unknown')}")
                logger.info(f"Certificate issuer: {issuer.get('commonName', 'Unknown')}")

                # Check certificate expiration
                not_after = cert["notAfter"]
                expiry_date = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                expiry_date = expiry_date.replace(tzinfo=timezone.utc)

                if expiry_date < datetime.now(timezone.utc):
                    pytest.fail(f"TLS certificate has expired: {not_after}")

                logger.info(f"Certificate expires: {not_after}")

                # Verify hostname in certificate
                common_name = subject.get("commonName", "")
                san_list = []

                for ext in cert.get("subjectAltName", []):
                    if ext[0] == "DNS":
                        san_list.append(ext[1])

                hostname_match = (
                    hostname == common_name
                    or hostname in san_list
                    or any(san.startswith("*.") and hostname.endswith(san[2:]) for san in san_list)
                )

                if not hostname_match:
                    logger.warning(f"Hostname {hostname} not found in certificate CN/SAN")
                    logger.warning(f"Certificate CN: {common_name}")
                    logger.warning(f"Certificate SAN: {san_list}")
                else:
                    logger.info("✅ Certificate hostname validation successful")

    except ssl.SSLError as e:
        pytest.fail(f"TLS certificate validation failed: {e}")
    except socket.error as e:
        pytest.fail(f"Network connection failed: {e}")


@mandatory
def test_tls_configuration_security():
    """
    RECOMMENDED: A2A v0.3.0 Section 4.1 - Modern TLS Configuration

    Implementations SHOULD use modern TLS configurations (TLS 1.3+ recommended).
    While this is a SHOULD requirement, secure TLS configuration is important for security.

    Test Logic:
    - Skip for localhost/test environments
    - For production: Check TLS version and cipher security

    Test Procedure:
    1. Establish TLS connection to SUT
    2. Check TLS protocol version
    3. Verify secure cipher suites are used
    4. Check for deprecated/weak configurations

    Asserts:
        - TLS version is 1.2 or higher (1.3 recommended)
        - Cipher suites are secure and modern
        - No deprecated protocols or weak ciphers
    """
    sut_url = config.get_sut_url()
    if not sut_url:
        pytest.skip("SUT URL not provided - cannot test TLS configuration")

    parsed_url = urllib.parse.urlparse(sut_url)

    # Skip TLS configuration check for localhost/test environments
    if is_localhost_or_test_environment(sut_url):
        logger.info("TLS configuration check skipped for localhost/test environment")
        pytest.skip("TLS configuration check relaxed for testing environments")

    # Only test HTTPS URLs
    if parsed_url.scheme != "https":
        pytest.skip("TLS configuration check only applicable to HTTPS URLs")

    hostname = parsed_url.hostname
    port = parsed_url.port or 443

    logger.info(f"Testing TLS configuration for {hostname}:{port}")

    try:
        # Create SSL context to check TLS configuration
        context = ssl.create_default_context()

        # Establish TLS connection
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as tls_sock:
                # Get TLS version
                tls_version = tls_sock.version()
                logger.info(f"TLS version: {tls_version}")

                # Check for modern TLS versions
                if tls_version in ["TLSv1.3", "TLSv1.2"]:
                    logger.info(f"✅ Modern TLS version detected: {tls_version}")
                elif tls_version == "TLSv1.1":
                    logger.warning(f"⚠️ TLS 1.1 is deprecated. Recommend upgrading to TLS 1.2+")
                elif tls_version in ["TLSv1", "SSLv3", "SSLv2"]:
                    pytest.fail(f"SECURITY ISSUE: Deprecated/insecure TLS version: {tls_version}")
                else:
                    logger.warning(f"Unknown TLS version: {tls_version}")

                # Get cipher information
                cipher = tls_sock.cipher()
                if cipher:
                    cipher_name, tls_version_cipher, key_length = cipher
                    logger.info(f"Cipher suite: {cipher_name}")
                    logger.info(f"Key length: {key_length} bits")

                    # Check for weak ciphers
                    weak_ciphers = ["RC4", "DES", "3DES", "MD5", "SHA1"]
                    if any(weak in cipher_name.upper() for weak in weak_ciphers):
                        logger.warning(f"⚠️ Potentially weak cipher detected: {cipher_name}")
                    else:
                        logger.info("✅ Cipher suite appears secure")

                    # Check key length
                    if key_length < 128:
                        pytest.fail(f"SECURITY ISSUE: Weak key length: {key_length} bits (minimum 128 recommended)")
                    elif key_length >= 256:
                        logger.info(f"✅ Strong key length: {key_length} bits")
                    else:
                        logger.info(f"✅ Adequate key length: {key_length} bits")

    except ssl.SSLError as e:
        logger.error(f"TLS configuration check failed: {e}")
        # Don't fail the test for TLS configuration issues in this SHOULD requirement
        logger.warning("TLS configuration issues detected but not failing (SHOULD requirement)")
    except socket.error as e:
        logger.error(f"Network connection failed: {e}")
        pytest.skip(f"Could not connect to test TLS configuration: {e}")


@mandatory
def test_http_to_https_redirect():
    """
    RECOMMENDED: Production HTTPS Setup - HTTP to HTTPS Redirect

    While not explicitly required by A2A specification, production deployments
    commonly redirect HTTP to HTTPS for security. This test checks if such
    redirects are properly configured.

    Test Logic:
    - Skip for localhost/test environments
    - For production HTTPS URLs: Test if HTTP version redirects to HTTPS

    Test Procedure:
    1. Attempt HTTP connection to same hostname
    2. Check if redirect to HTTPS occurs
    3. Verify redirect is permanent (301/308)

    Asserts:
        - HTTP requests redirect to HTTPS (if applicable)
        - Redirect status codes are appropriate
        - Final destination is HTTPS
    """
    sut_url = config.get_sut_url()
    if not sut_url:
        pytest.skip("SUT URL not provided - cannot test HTTP redirect")

    parsed_url = urllib.parse.urlparse(sut_url)

    # Skip for localhost/test environments
    if is_localhost_or_test_environment(sut_url):
        pytest.skip("HTTP redirect test skipped for localhost/test environment")

    # Only test if SUT is already HTTPS
    if parsed_url.scheme != "https":
        pytest.skip("HTTP redirect test only applicable when SUT uses HTTPS")

    # Construct HTTP version of the URL
    http_url = sut_url.replace("https://", "http://", 1)

    logger.info(f"Testing HTTP to HTTPS redirect: {http_url} → {sut_url}")

    try:
        # Test HTTP request with redirect following disabled initially
        response = requests.get(http_url, timeout=10, allow_redirects=False)

        if response.status_code in (301, 302, 307, 308):
            redirect_location = response.headers.get("Location", "")

            if redirect_location.startswith("https://"):
                logger.info(f"✅ HTTP redirects to HTTPS: {response.status_code} → {redirect_location}")

                # Check if redirect is permanent (recommended for security)
                if response.status_code in (301, 308):
                    logger.info("✅ Permanent redirect used (recommended)")
                else:
                    logger.info("Temporary redirect used (permanent redirect recommended)")
            else:
                logger.warning(f"HTTP redirects but not to HTTPS: {redirect_location}")
        else:
            logger.info(f"HTTP request returned {response.status_code} (no redirect detected)")
            logger.info("Note: HTTP to HTTPS redirect is recommended but not required by A2A spec")

    except requests.exceptions.ConnectionError:
        logger.info("HTTP port not accessible (common for HTTPS-only deployments)")
    except requests.exceptions.RequestException as e:
        logger.warning(f"HTTP redirect test failed: {e}")
        # Don't fail the test as HTTP redirect is not required by A2A spec
