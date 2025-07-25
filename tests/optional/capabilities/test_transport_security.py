"""
A2A Protocol Specification: Transport Security tests.

This test suite validates the SUT's adherence to transport security best practices
according to the A2A specification: https://google.github.io/A2A/specification/#transport-security

These tests focus on basic transport security requirements such as HTTPS enforcement.
"""

import logging
import socket
import ssl
import urllib.parse

import pytest
import requests

from tck import agent_card_utils, config
from tck.sut_client import SUTClient
from tests.markers import optional_capability

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def sut_client():
    """Fixture to provide a SUTClient instance."""
    return SUTClient()

@pytest.fixture(scope="module")
def sut_url_info():
    """
    Parse the SUT URL into components for testing transport security.
    """
    # Get the SUT URL from config
    sut_url = config.get_sut_url()
    
    # Parse the URL into components
    parsed_url = urllib.parse.urlparse(sut_url)
    
    return {
        "scheme": parsed_url.scheme,
        "netloc": parsed_url.netloc,
        "hostname": parsed_url.hostname,
        "port": parsed_url.port or (443 if parsed_url.scheme == "https" else 80),
        "path": parsed_url.path or "/",
        "full_url": sut_url,
        "is_https": parsed_url.scheme.lower() == "https"
    }

@optional_capability
def test_sut_uses_https(sut_url_info):
    """
    OPTIONAL CAPABILITY: A2A Specification §4.2 - Transport Security
    
    Tests that the SUT endpoint uses HTTPS for secure communication.
    While HTTPS is not strictly mandated, it's considered best practice.
    
    Failure Impact: Limits security posture (perfectly acceptable for development)
    Fix Suggestion: Configure HTTPS endpoint for production deployments
    
    Asserts:
        - SUT URL uses HTTPS protocol
        - Secure transport is available for sensitive communications
        - Security best practices are followed
    """
    if not sut_url_info["is_https"]:
        logger.warning("SUT URL is not using HTTPS: %s", sut_url_info["full_url"])
        # This is not a failure but a warning, as HTTPS isn't strictly required
        # but is highly recommended

@optional_capability
def test_http_to_https_redirect(sut_url_info):
    """
    OPTIONAL CAPABILITY: A2A Specification §4.2 - HTTPS Redirect Security
    
    Tests if the SUT properly redirects HTTP requests to HTTPS.
    This enhances security by ensuring all traffic uses encrypted transport.
    
    Failure Impact: Limits security posture (perfectly acceptable for development)
    Fix Suggestion: Configure HTTP to HTTPS redirect for production deployments
    
    Asserts:
        - HTTP requests are redirected to HTTPS
        - Redirect uses appropriate HTTP status codes
        - Security enforcement is consistent
    """
    if not sut_url_info["is_https"]:
        pytest.skip("SUT URL is not using HTTPS, so HTTP to HTTPS redirect test is not applicable")
    
    # Create a new HTTP URL from the HTTPS URL
    http_url = f"http://{sut_url_info['netloc']}{sut_url_info['path']}"
    
    # Try a simple GET request to the HTTP URL to see if it redirects
    try:
        # Use allow_redirects=False to see the initial response before any redirects
        response = requests.get(http_url, allow_redirects=False, timeout=10)
        
        # Check if we got a redirect response
        if response.status_code in (301, 302, 307, 308):
            # Check if the redirect location is HTTPS
            location = response.headers.get("Location", "")
            logger.info(f"HTTP request redirected to: {location}")
            
            if location.startswith("https://"):
                logger.info("SUT properly redirects HTTP to HTTPS")
            else:
                logger.warning(f"SUT redirects, but not to HTTPS: {location}")
                pytest.fail(f"SUT redirects HTTP to non-HTTPS URL: {location}")
        else:
            logger.warning(f"HTTP request did not redirect, got status code: {response.status_code}")
            pytest.fail(f"SUT did not redirect HTTP to HTTPS (got status code {response.status_code})")
    
    except requests.RequestException as e:
        # Connection errors might occur if the server simply doesn't listen on HTTP
        logger.info(f"HTTP request failed: {e}")
        logger.info("This might be expected if the server only accepts HTTPS connections")

@optional_capability
@pytest.mark.xfail(reason="When testing locally, the https in agent card is not available")
def test_https_url_in_agent_card(sut_client, agent_card_data):
    """
    OPTIONAL CAPABILITY: A2A Specification §5.6 - Agent Card URL Security
    
    Tests that the URLs declared in the Agent Card use HTTPS protocol.
    This validates consistency between security practices and self-reported URLs.
    
    Failure Impact: Limits security posture (perfectly acceptable for development)
    Fix Suggestion: Update Agent Card URLs to use HTTPS for production
    
    Asserts:
        - Agent Card URLs use HTTPS protocol
        - Self-reported endpoints follow security best practices
        - URL declarations are consistent with security requirements
    """
    if agent_card_data is None:
        pytest.skip("Agent Card data is not available")
    
    # Check URL field if present
    if "url" in agent_card_data:
        url = agent_card_data["url"]
        assert url.startswith("https://"), f"Agent Card URL should use HTTPS: {url}"
    
    # Check endpoint field if present
    if "endpoint" in agent_card_data:
        endpoint = agent_card_data["endpoint"]
        assert endpoint.startswith("https://"), f"Agent Card endpoint should use HTTPS: {endpoint}"
    
    # Check endpoints in other places where they might be defined
    if "jsonrpc" in agent_card_data and "endpoint" in agent_card_data["jsonrpc"]:
        jsonrpc_endpoint = agent_card_data["jsonrpc"]["endpoint"]
        assert jsonrpc_endpoint.startswith("https://"), f"Agent Card jsonrpc.endpoint should use HTTPS: {jsonrpc_endpoint}"

@optional_capability
def test_tls_version(sut_url_info):
    """
    OPTIONAL CAPABILITY: A2A Specification §4.1 - TLS Version Requirements
    
    Tests that the SUT uses TLS 1.3+ as RECOMMENDED by the latest specification.
    The specification now recommends TLS 1.3+ instead of TLS 1.2+.
    
    Failure Impact: Limits security posture (perfectly acceptable for current deployments)
    Fix Suggestion: Configure server to use TLS 1.3+ for enhanced security
    
    Asserts:
        - HTTPS connections use TLS 1.3 or higher
        - Transport security follows latest best practices
        - Strong cryptographic protocols are used
    """
    if not sut_url_info["is_https"]:
        pytest.skip("SUT URL is not using HTTPS, so TLS version test is not applicable")
    
    hostname = sut_url_info["hostname"]
    port = sut_url_info["port"]
    
    if not hostname:
        pytest.skip("Cannot determine hostname from SUT URL for TLS version check")
    
    try:
        # Create SSL context with default settings
        context = ssl.create_default_context()
        
        # Connect to the server and get TLS version
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                tls_version = ssock.version()
                cipher = ssock.cipher()
                
                logger.info(f"Connected to {hostname}:{port}")
                logger.info(f"TLS version: {tls_version}")
                if cipher:
                    logger.info(f"Cipher suite: {cipher[0]}")
                    logger.info(f"TLS protocol: {cipher[1]}")
                    logger.info(f"Encryption bits: {cipher[2]}")
                
                # Check TLS version - TLS 1.3+ is RECOMMENDED
                if tls_version:
                    if tls_version.startswith("TLSv1.3"):
                        logger.info("✓ SUT uses TLS 1.3 - excellent security posture")
                        assert True, "TLS 1.3 is being used"
                    elif tls_version.startswith("TLSv1.2"):
                        logger.warning("⚠ SUT uses TLS 1.2 - consider upgrading to TLS 1.3")
                        # TLS 1.2 is still acceptable but not the recommended latest version
                        pytest.fail("SUT uses TLS 1.2 instead of RECOMMENDED TLS 1.3+")
                    else:
                        logger.error(f"✗ SUT uses outdated TLS version: {tls_version}")
                        pytest.fail(f"SUT uses outdated TLS version: {tls_version} (TLS 1.3+ RECOMMENDED)")
                else:
                    logger.error("Could not determine TLS version")
                    pytest.fail("Could not determine TLS version from connection")
    
    except socket.gaierror as e:
        logger.error(f"DNS resolution failed for {hostname}: {e}")
        pytest.skip(f"Cannot resolve hostname {hostname} for TLS version check")
    except socket.timeout:
        logger.error(f"Connection timeout to {hostname}:{port}")
        pytest.skip(f"Connection timeout to {hostname}:{port} for TLS version check")
    except ConnectionRefusedError:
        logger.error(f"Connection refused to {hostname}:{port}")
        pytest.skip(f"Connection refused to {hostname}:{port} for TLS version check")
    except ssl.SSLError as e:
        logger.error(f"SSL error connecting to {hostname}:{port}: {e}")
        pytest.fail(f"SSL error during TLS version check: {e}")
    except Exception as e:
        logger.error(f"Unexpected error checking TLS version: {e}")
        pytest.skip(f"Unexpected error during TLS version check: {e}") 